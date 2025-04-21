import queue
import threading
import time

task_queue = queue.Queue()

def worker():
    while True:
        func, args, kwargs = task_queue.get()
        try:
            func(*args, **kwargs)
        except Exception as e:
            print(f"Error processing task: {e}")
        task_queue.task_done()
        time.sleep(0.1)  # small delay to reduce CPU usage

threading.Thread(target=worker, daemon=True).start()


def enqueue_task(func, *args, **kwargs):
    task_queue.put((func, args, kwargs))