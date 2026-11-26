import threading
import time
import platform
try:
    import resource
except ImportError:
    resource = None
from pathlib import Path
import psutil


class Measurement:
    def __enter__(self):
        self.start = time.perf_counter()
        self.peak = 0
        self.stop = threading.Event()
        def sample():
            proc = psutil.Process()
            while not self.stop.is_set():
                self.peak = max(self.peak,proc.memory_info().rss)
                self.stop.wait(.02)
        self.thread = threading.Thread(target=sample,daemon=True)
        self.thread.start()
        return self

    def __exit__(self,*args):
        self.stop.set()
        self.thread.join()
        self.duration = time.perf_counter()-self.start

    def result(self):
        usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss if resource else 0
        return dict(duration_seconds=round(self.duration,3), peak_rss_bytes_sampled=self.peak,
                    process_lifetime_peak_rss_bytes=int(usage*(1 if platform.system()=='Darwin' else 1024)) if resource else None,
                    memory_measurement='psutil RSS sampled every 20 ms; ru_maxrss process lifetime')


def disk_usage(root):
    files = [p for p in Path(root).rglob('*') if p.is_file()]
    return dict(total_bytes=sum(p.stat().st_size for p in files), file_count=len(files),
                parquet_file_count=sum(p.suffix=='.parquet' for p in files))
