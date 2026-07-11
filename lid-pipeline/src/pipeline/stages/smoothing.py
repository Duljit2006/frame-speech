import math
from typing import List, Dict
from collections import Counter

from ...config import settings

class LanguageSmoother:
    """
    Post-processes the raw LID predictions from overlapping sliding windows
    into a clean, human-readable language timeline.
    
    Algorithm (Time-Bin Majority Voting):
    1. Filter out predictions from segments shorter than MIN_SEGMENT_DURATION
    2. Apply language family grouping (e.g., merge Urdu into Hindi)
    3. Divide the full audio timeline into small fixed time-bins (e.g., 0.5s each)
    4. For each time-bin, collect all overlapping window predictions
    5. Run a confidence-weighted majority vote to pick the winning language per bin
    6. Merge consecutive bins with the same language into continuous blocks
    7. Drop any final merged blocks shorter than MIN_MERGED_DURATION
    """
    def __init__(self):
        self.time_bin_size = settings.SMOOTHING_TIME_BIN_SECONDS
        self.min_segment_duration = settings.MIN_SEGMENT_DURATION
        self.min_merged_duration = settings.MIN_MERGED_DURATION
        self.family_map = settings.LANGUAGE_FAMILY_MAP

    def process(self, raw_results: List[Dict]) -> List[Dict]:
        """
        Args:
            raw_results: List of dicts from LIDProcessor, e.g.:
                [{'start': 1.2, 'end': 4.2, 'language': 'hi: Hindi', 
                  'confidence': 0.95, 'source': 'speechbrain'}, ...]
        
        Returns:
            List of smoothed language blocks, e.g.:
                [{'start': 0.0, 'end': 65.5, 'language': 'Hindi', 
                  'confidence': 0.94, 'window_count': 42}, ...]
        """
        if not raw_results:
            return []

        # Step 1: Filter out very short segments and failed/skipped predictions
        filtered = self._filter_short_and_failed(raw_results)
        if not filtered:
            return []
        
        # Step 2: Normalize language labels and apply family grouping
        normalized = self._normalize_languages(filtered)
        
        # Step 3: Build time-bin grid and run majority voting
        timeline_start = min(r['start'] for r in normalized)
        timeline_end = max(r['end'] for r in normalized)
        bin_labels = self._majority_vote(normalized, timeline_start, timeline_end)
        
        # Step 4: Merge consecutive bins with the same language
        merged = self._merge_bins(bin_labels, timeline_start)
        
        # Step 5: Absorb tiny glitch blocks into their neighbors
        merged = self._absorb_tiny_blocks(merged)
        
        return merged

    def _filter_short_and_failed(self, results: List[Dict]) -> List[Dict]:
        """Remove predictions from segments too short to be reliable, 
        and skip failed/unknown predictions."""
        filtered = []
        for r in results:
            duration = r['end'] - r['start']
            if duration < self.min_segment_duration:
                continue
            if r.get('source') in ('skipped', 'failed') or r.get('language') == 'unknown':
                continue
            filtered.append(r)
        return filtered

    def _normalize_languages(self, results: List[Dict]) -> List[Dict]:
        """Normalize language labels to short codes and apply family grouping."""
        normalized = []
        for r in results:
            lang = r['language']
            
            # Extract short code if format is "hi: Hindi"
            if ': ' in lang:
                short_code = lang.split(': ')[0].strip()
                full_name = lang.split(': ')[1].strip()
            else:
                short_code = lang.strip()
                full_name = lang.strip()
            
            # Apply family grouping (e.g., ur -> hi)
            mapped_code = self.family_map.get(short_code, short_code)
            
            normalized.append({
                **r,
                'lang_code': mapped_code,
                'lang_display': full_name if mapped_code == short_code else self._get_display_name(mapped_code),
            })
        return normalized

    def _get_display_name(self, code: str) -> str:
        """Get a human-readable display name for a language code."""
        names = {
            'hi': 'Hindi', 'en': 'English', 'ur': 'Urdu', 'pa': 'Punjabi',
            'bn': 'Bengali', 'mr': 'Marathi', 'ta': 'Tamil', 'te': 'Telugu',
            'gu': 'Gujarati', 'kn': 'Kannada', 'ml': 'Malayalam', 'as': 'Assamese',
            'de': 'German', 'fr': 'French', 'es': 'Spanish', 'ja': 'Japanese',
            'zh': 'Chinese', 'ar': 'Arabic', 'ko': 'Korean', 'ru': 'Russian',
            'ms': 'Malay', 'tl': 'Tagalog', 'cy': 'Welsh', 'he': 'Hebrew'
        }
        return names.get(code, code)

    def _majority_vote(self, results: List[Dict], start: float, end: float) -> List[Dict]:
        """
        Divide the timeline into fixed-size bins and run confidence-weighted 
        majority voting across all overlapping windows for each bin.
        """
        num_bins = math.ceil((end - start) / self.time_bin_size)
        bins = []
        
        for i in range(num_bins):
            bin_start = start + i * self.time_bin_size
            bin_end = bin_start + self.time_bin_size
            
            # Collect all predictions that overlap with this bin
            votes = {}  # lang_code -> total weighted score
            for r in results:
                if r['end'] > bin_start and r['start'] < bin_end:
                    lang = r['lang_code']
                    weight = r['confidence']
                    votes[lang] = votes.get(lang, 0.0) + weight
            
            if votes:
                # Pick the language with the highest total weighted score
                winner = max(votes, key=votes.get)
                total_weight = sum(votes.values())
                winner_weight = votes[winner]
                bins.append({
                    'bin_start': round(bin_start, 3),
                    'bin_end': round(bin_end, 3),
                    'language': winner,
                    'confidence': round(winner_weight / total_weight, 4) if total_weight > 0 else 0,
                    'vote_count': len([r for r in results if r['end'] > bin_start and r['start'] < bin_end]),
                })
            else:
                # No predictions cover this bin (silence gap)
                bins.append({
                    'bin_start': round(bin_start, 3),
                    'bin_end': round(bin_end, 3),
                    'language': None,
                    'confidence': 0,
                    'vote_count': 0,
                })
        
        return bins

    def _merge_bins(self, bins: List[Dict], timeline_start: float) -> List[Dict]:
        """Merge consecutive bins with the same language into continuous blocks."""
        if not bins:
            return []
        
        merged = []
        current_lang = bins[0]['language']
        current_start = bins[0]['bin_start']
        confidence_sum = bins[0]['confidence']
        vote_sum = bins[0]['vote_count']
        bin_count = 1
        
        for i in range(1, len(bins)):
            b = bins[i]
            if b['language'] == current_lang:
                # Same language, extend the block
                confidence_sum += b['confidence']
                vote_sum += b['vote_count']
                bin_count += 1
            else:
                # Language changed, save previous block
                if current_lang is not None:
                    merged.append({
                        'start': round(current_start, 3),
                        'end': round(bins[i-1]['bin_end'], 3),
                        'language': self._get_display_name(current_lang),
                        'lang_code': current_lang,
                        'confidence': round(confidence_sum / bin_count, 4),
                        'window_count': vote_sum,
                    })
                # Start new block
                current_lang = b['language']
                current_start = b['bin_start']
                confidence_sum = b['confidence']
                vote_sum = b['vote_count']
                bin_count = 1
        
        # Don't forget the last block
        if current_lang is not None:
            merged.append({
                'start': round(current_start, 3),
                'end': round(bins[-1]['bin_end'], 3),
                'language': self._get_display_name(current_lang),
                'lang_code': current_lang,
                'confidence': round(confidence_sum / bin_count, 4),
                'window_count': vote_sum,
            })
        
        return merged

    def _absorb_tiny_blocks(self, blocks: List[Dict]) -> List[Dict]:
        """
        Iterates over the merged blocks and absorbs any block shorter than 
        a strict threshold (e.g., 2.5 seconds) into the neighboring block.
        This erases tiny glitches like 1.5s of 'Welsh' in the middle of Hindi.
        """
        if not blocks:
            return []
            
        GLITCH_THRESHOLD = 2.5  # seconds
        
        # We will do a multi-pass absorption until no tiny blocks remain.
        # This handles cases where multiple tiny blocks are adjacent.
        changed = True
        while changed and len(blocks) > 1:
            changed = False
            new_blocks = []
            
            i = 0
            while i < len(blocks):
                block = blocks[i]
                duration = block['end'] - block['start']
                
                # Is it a tiny glitch block?
                if duration < GLITCH_THRESHOLD:
                    # Find the longest neighbor to absorb it
                    left_neighbor = new_blocks[-1] if len(new_blocks) > 0 else None
                    right_neighbor = blocks[i+1] if i + 1 < len(blocks) else None
                    
                    target = None
                    if left_neighbor and right_neighbor:
                        # Absorb into whichever neighbor is longer
                        if (left_neighbor['end'] - left_neighbor['start']) >= (right_neighbor['end'] - right_neighbor['start']):
                            target = left_neighbor
                        else:
                            target = right_neighbor
                    elif left_neighbor:
                        target = left_neighbor
                    elif right_neighbor:
                        target = right_neighbor
                        
                    if target:
                        # Change this block's language to match the target neighbor
                        block['language'] = target['language']
                        block['lang_code'] = target['lang_code']
                        changed = True
                
                new_blocks.append(block)
                i += 1
                
            blocks = new_blocks
            
            # If we changed labels, we need to re-merge consecutive identical labels
            if changed:
                re_merged = []
                current = blocks[0]
                for b in blocks[1:]:
                    if b['language'] == current['language']:
                        # Extend current block
                        current['end'] = b['end']
                        current['window_count'] += b['window_count']
                        # Average confidence
                        current['confidence'] = round((current['confidence'] + b['confidence']) / 2, 4)
                    else:
                        re_merged.append(current)
                        current = b
                re_merged.append(current)
                blocks = re_merged
                
        return blocks

