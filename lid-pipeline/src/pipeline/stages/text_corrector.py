import os
import json
from typing import List, Dict, Any, Optional
from ...config import settings

class TextCorrectionProcessor:
    """
    Post-transcription text correction stage powered by Google Gemini API.
    
    Implements a Full-Context Two-Pass algorithm:
      1. Reads the ENTIRE transcript to understand full context.
      2. Reconstructs fragmented segments into proper, complete sentences.
      3. Applies targeted orthographic rules (e.g., Assamese 'ৰ' correction).
      4. Preserves English loanwords in Latin script.
      5. Generates new timestamps mapping 1 sentence = 1 timestamp.
    """
    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        self.api_key = api_key or settings.GEMINI_API_KEY or os.environ.get("GEMINI_API_KEY")
        # Re-read model from env at runtime to ensure .env changes are always picked up
        self.model_name = model_name or settings.GEMINI_MODEL or os.environ.get("GEMINI_MODEL") or "gemini-3.5-flash"
        self.client = None
        
        if self.api_key:
            try:
                from google import genai
                self.client = genai.Client(api_key=self.api_key)
                print(f"  [TextCorrector] Gemini client initialized. Model: '{self.model_name}'.")
            except ImportError:
                print("  [TextCorrector] Warning: 'google-genai' package not installed. Skipping text correction.")
            except Exception as e:
                print(f"  [TextCorrector] Warning: Failed to initialize Gemini client: {e}")
        else:
            print("  [TextCorrector] No GEMINI_API_KEY configured. Skipping post-transcription text correction.")

    def correct(self, segments: List[Dict[str, Any]], progress_callback=None) -> List[Dict[str, Any]]:
        if not self.client or not segments:
            return segments
            
        print(f"  [TextCorrector] Sending {len(segments)} segments to Gemini for full-context analysis...")
        if progress_callback:
            progress_callback("Gemini: Analyzing full context and restructuring sentences...")
            
        try:
            return self._process_full_context(segments)
        except Exception as e:
            import traceback
            print(f"  [TextCorrector] Error during full-context correction: {e}")
            traceback.print_exc()
            print("  [TextCorrector] Falling back to original uncorrected text.")
            return segments

    def _process_full_context(self, segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Processes the transcript in batches while passing the full transcript as 
        read-only context to avoid max-token limits on long 12+ minute videos.
        """
        if not segments:
            return []

        from google.genai import types

        # Create a lookup for timestamps and full context string
        segment_map = {seg["id"]: seg for seg in segments}
        full_context_text = " ".join([seg["text"] for seg in segments])
        
        BATCH_SIZE = 100
        new_segments = []
        new_id = 1
        
        for i in range(0, len(segments), BATCH_SIZE):
            batch = segments[i:i + BATCH_SIZE]
            
            payload = []
            for seg in batch:
                payload.append({
                    "language": seg["language"],
                    "start": seg["start"],
                    "end": seg["end"],
                    "text": seg["text"]
                })
                
            system_instruction = (
                "You are an expert multilingual AI text correction engine. You are provided with a batch of segments "
                "from a longer transcript. Your task is to restructure this specific batch.\n\n"
                "Rules:\n"
                "1. Use the provided 'Full Transcript Context' to understand the topic and speaker flow, but ONLY return corrections for the segments in the 'Batch to Correct'.\n"
                "2. Sentence Restructuring: Reconstruct the fragmented text into complete, grammatically correct sentences. "
                "Merge incomplete segments together. Do not output fragmented half-sentences.\n"
                "3. Enforce Native Scripts: Convert romanized/phonetic text into the proper native script for the tagged language (e.g., Devanagari for Hindi, Gurmukhi for Punjabi, Bengali for Bengali, etc.), EXCEPT for English words.\n"
                "4. Assamese Orthography Rule: Assamese speech was transcribed using a Bengali model. For segments tagged as 'Assamese', "
                "you MUST correct the text to use proper Assamese characters (e.g., replace Bengali 'র' with Assamese 'ৰ', and 'ব' with 'ৱ').\n"
                "5. STRICT Code-Switching Rule: You MUST perform word-level code-switching for ALL languages. If a speaker uses English loanwords, phrases, or full English sentences (e.g., 'In Punjabi we say', 'press conference', 'MBA', 'trump card'), "
                "you MUST write those specific words in English (Latin script) even if the rest of the sentence is in an Indic script (Devanagari, Gujarati, Bengali, Tamil, etc.). DO NOT transliterate English words into Indic scripts (e.g., output 'In Hindi we say', NOT 'इन हिंदी वी से').\n"
                "6. Clean Hallucinations: Remove any nonsensical character salad or repetitive gibberish.\n"
                "7. DO NOT omit, summarize, or delete any valid information. Ensure EVERY word spoken in the input is represented in the output, just restructured into proper sentences.\n"
                "8. Return ONLY a valid JSON array of objects. Each object represents ONE complete sentence and MUST contain:\n"
                "   - 'text': The fully corrected, complete sentence.\n"
                "   - 'language': The dominant language of this sentence.\n"
                "   - 'start': The precise start timestamp in seconds (use the start of the first merged segment, or estimate if split).\n"
                "   - 'end': The precise end timestamp in seconds (use the end of the last merged segment, or estimate if split).\n\n"
                "--- EXAMPLES ---\n"
                "Input: [{\"language\": \"Hindi\", \"start\": 0.1, \"end\": 1.5, \"text\": \"इन पंजाबी वी से समा.\"}]\n"
                "Output: [{\"text\": \"In Punjabi we say समा।\", \"language\": \"Hindi\", \"start\": 0.1, \"end\": 1.5}]\n\n"
                "Input: [{\"language\": \"Gujarati\", \"start\": 2.0, \"end\": 4.5, \"text\": \"તેન્દી વી સે માં, મમી, એન ઉર્ધુ વી સે અમ્મી\"}]\n"
                "Output: [{\"text\": \"In Hindi we say માં, mummy, and in Urdu we say અમ્મી।\", \"language\": \"Gujarati\", \"start\": 2.0, \"end\": 4.5}]\n\n"
                "Input: [{\"language\": \"Bengali\", \"start\": 5.0, \"end\": 7.0, \"text\": \"সেখানে ইধারনে প্রেস কোন্ফ্রেন্স করতে পারেনা\"}]\n"
                "Output: [{\"text\": \"সেখানে এধরনের press conference করতে পারে না।\", \"language\": \"Bengali\", \"start\": 5.0, \"end\": 7.0}]\n\n"
                "Do NOT include markdown formatting (like ```json), just return the raw JSON array."
            )
            
            prompt = (
                f"--- Full Transcript Context (Read Only) ---\n"
                f"{full_context_text}\n\n"
                f"--- Batch to Correct ---\n"
                f"{json.dumps(payload, ensure_ascii=False, indent=2)}"
            )
            
            try:
                import time
                # Pace requests by waiting 3 seconds before each new batch (avoids rapid spiking)
                if i > 0:
                    time.sleep(3)
                    
                print(f"  [TextCorrector] Sending batch {i//BATCH_SIZE + 1} to Gemini ({len(batch)} segments)...")
                
                max_retries = 4
                response = None
                
                for attempt in range(max_retries):
                    try:
                        response = self.client.models.generate_content(
                            model=self.model_name,
                            contents=prompt,
                            config=types.GenerateContentConfig(
                                system_instruction=system_instruction,
                                response_mime_type="application/json",
                                temperature=0.2,
                            )
                        )
                        break  # Success
                    except Exception as api_err:
                        err_str = str(api_err)
                        if ("503" in err_str or "UNAVAILABLE" in err_str or "429" in err_str) and attempt < max_retries - 1:
                            # If the API tells us exactly how long to wait, extract it. Otherwise fallback to 15s.
                            import re
                            match = re.search(r"retry in ([0-9.]+)s", err_str)
                            delay = float(match.group(1)) + 1 if match else 15.0
                            
                            print(f"  [TextCorrector] Gemini API busy. Retrying in {delay:.1f}s... (Attempt {attempt+1}/{max_retries})")
                            time.sleep(delay)
                        else:
                            raise api_err
                            
                if not response:
                    raise Exception("Failed to get response after retries.")
                
                response_text = response.text.strip()
                if response_text.startswith("```json"):
                    response_text = response_text[7:]
                if response_text.startswith("```"):
                    response_text = response_text[3:]
                if response_text.endswith("```"):
                    response_text = response_text[:-3]
                response_text = response_text.strip()
                
                corrected_data = json.loads(response_text)
                
                # Build new segments
                for item in corrected_data:
                    if "text" not in item or "start" not in item or "end" not in item:
                        continue
                        
                    new_segments.append({
                        "id": new_id,
                        "start": float(item["start"]),
                        "end": float(item["end"]),
                        "text": item["text"].strip(),
                        "language": item.get("language", "Unknown"),
                        "words": []
                    })
                    new_id += 1
            except Exception as e:
                print(f"  [TextCorrector] Error on batch {i//BATCH_SIZE + 1}: {e}. Falling back to uncorrected segments.")
                # Fallback to uncorrected for this batch
                for seg in batch:
                    new_segments.append({
                        "id": new_id,
                        "start": seg["start"],
                        "end": seg["end"],
                        "text": seg["text"],
                        "language": seg["language"],
                        "words": []
                    })
                    new_id += 1
                    
        return new_segments
