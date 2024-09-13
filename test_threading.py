import threading
import time
semaphore = threading.Semaphore(1)

def _low_res_processing(semaphore):
    while True:
        with semaphore:
            print("Low-res processing started")
            time.sleep(1)  # Simulate some processing time
            print("Low-res processing finished")
        time.sleep(1)

def _high_res_saving(semaphore):
    while True:
        with semaphore:
            print("High-res saving started")
            time.sleep(1)  # Simulate some processing time
            print("High-res saving finished")
        time.sleep(1)

# Start both threads
threading.Thread(target=_low_res_processing, args=(semaphore,)).start()
threading.Thread(target=_high_res_saving, args=(semaphore,)).start()

print("Main thread continues to run")