import os
import cv2
import time
import threading
import queue
from datetime import datetime
import config
from collections import deque

class VideoRecorder:
    def __init__(self):
        self.recording = False
        self.frame_queue = queue.Queue(maxsize=100)
        self.recording_thread = None
        self.writer = None
        self.current_file = None
        self.segment_start_time = 0
        self.frame_buffer = deque(maxlen=config.INTRUDER_CLIP_SECONDS_BEFORE * config.INTRUDER_RECORDING_FPS)
        
    def log_message(self, message, is_error=False):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {'ERROR: ' if is_error else ''}[Recorder] {message}")
    
    def start(self):
        if self.recording:
            return
            
        self.recording = True
        self.recording_thread = threading.Thread(target=self._recording_worker, daemon=True)
        self.recording_thread.start()
        self.log_message("Video recording started")
        
    def stop(self):
        self.recording = False
        if self.writer:
            time.sleep(0.1)
            self.writer.release()
            self.writer = None
        self.log_message("Video recording stopped")
        
    def add_frame(self, frame):
        if not self.recording:
            return
            
        try:
            resized_frame = cv2.resize(frame, config.RECORDING_RESOLUTION)
            self.frame_queue.put_nowait(resized_frame)
        except queue.Full:
            pass
            
        self.frame_buffer.append(frame.copy())
    
    def _create_new_segment(self):
        if self.writer:
            self.writer.release()
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"recording_{timestamp}.avi"
        filepath = os.path.join(config.RECORDINGS_DIR, filename)
        
        fourcc = cv2.VideoWriter_fourcc(*'XVID')
        self.writer = cv2.VideoWriter(
            filepath, 
            fourcc, 
            config.RECORDING_FPS,
            config.RECORDING_RESOLUTION,
            True
        )
        
        self.current_file = filepath
        self.segment_start_time = time.time()
        self.log_message(f"Created new recording segment: {filename}")
    
    def _recording_worker(self):
        self._create_new_segment()
        
        while self.recording:
            if time.time() - self.segment_start_time > (config.RECORDING_SEGMENT_MINUTES * 60):
                self._create_new_segment()
            
            try:
                frame = self.frame_queue.get(timeout=1.0)
                
                if self.writer:
                    self.writer.write(frame)
                    
                self.frame_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                self.log_message(f"Error in recording thread: {str(e)}", True)
                time.sleep(1)
    
    def save_intruder_clip(self, frame, additional_seconds=None):
        if additional_seconds is None:
            additional_seconds = config.INTRUDER_CLIP_SECONDS_AFTER
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"intruder_{timestamp}.avi"
        filepath = os.path.join(config.INTRUDERS_VIDEOS_DIR, filename)
        
        fourcc = cv2.VideoWriter_fourcc(*'XVID')
        h, w = frame.shape[:2]
        writer = cv2.VideoWriter(filepath, fourcc, config.INTRUDER_RECORDING_FPS, (w, h), True)
        
        for buffered_frame in self.frame_buffer:
            writer.write(buffered_frame)
            
        writer.write(frame.copy())
        
        additional_frames_needed = additional_seconds * config.INTRUDER_RECORDING_FPS
        
        def collect_additional_frames():
            frames_added = 0
            start_time = time.time()
            
            while frames_added < additional_frames_needed:
                if time.time() - start_time > additional_seconds * 2:
                    break
                    
                if len(self.frame_buffer) > 0:
                    newest_frame = self.frame_buffer[-1]
                    writer.write(newest_frame)
                    frames_added += 1
                    
                time.sleep(1.0 / config.INTRUDER_RECORDING_FPS)
                
            writer.release()
            self.log_message(f"Saved intruder clip: {filename}")
            
        threading.Thread(target=collect_additional_frames, daemon=True).start()
        
        return filepath

recorder = VideoRecorder()