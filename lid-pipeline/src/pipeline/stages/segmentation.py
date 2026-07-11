from typing import List, Dict
from ...config import settings

class SegmentationEngine:
    """
    Takes continuous speech intervals from VAD and chops them into fixed-size 
    overlapping sliding windows. This is crucial because LID models perform best 
    on fixed-length audio contexts (e.g., 3-second chunks).
    """
    def __init__(self):
        self.window_size = settings.WINDOW_SIZE_SECONDS
        self.step_size = settings.WINDOW_STEP_SECONDS

    def process(self, vad_intervals: List[Dict[str, float]]) -> List[Dict[str, float]]:
        """
        Args:
            vad_intervals: List of dicts e.g., [{'start': 1.2, 'end': 5.5}, ...]
            
        Returns:
            List of window dicts e.g., [{'start': 1.2, 'end': 4.2}, {'start': 2.2, 'end': 5.2}, ...]
        """
        windows = []
        
        for interval in vad_intervals:
            start = interval['start']
            end = interval['end']
            duration = end - start
            
            # If the speech segment is shorter than a single window size,
            # just keep the segment as is. The LID model can handle slightly shorter clips.
            if duration <= self.window_size:
                windows.append({
                    'start': round(start, 3),
                    'end': round(end, 3)
                })
                continue
                
            # Sliding window logic for longer segments
            current_start = start
            while current_start + self.window_size <= end:
                windows.append({
                    'start': round(current_start, 3),
                    'end': round(current_start + self.window_size, 3)
                })
                current_start += self.step_size
                
            # Handle the remainder (the tail end of the segment)
            # If there is leftover audio that didn't fit into the last full window,
            # we capture a final window aligned exactly to the end of the segment.
            if current_start < end and (end - current_start) > 0.5: # Ignore tiny remainders < 0.5s
                last_window_start = max(start, end - self.window_size)
                
                # Prevent duplicating a window if it happens to align perfectly
                if not windows or windows[-1]['start'] != round(last_window_start, 3):
                    windows.append({
                        'start': round(last_window_start, 3),
                        'end': round(end, 3)
                    })
                    
        return windows
