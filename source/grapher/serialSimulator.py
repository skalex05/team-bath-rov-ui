import csv
import time

def simulate_serial_data(csv_file, txt_file, data_rate_hz=500):
    ''' Just some random file that reads csv and writes it to txt. Can't be run simulataneously'''
    with open(csv_file, 'r') as csvfile:
        reader = csv.reader(csvfile)
        headers = next(reader)  # Skip headers
        data_lines = list(reader)

    print("read data")
        
    total_lines = len(data_lines)
    interval = 1 / data_rate_hz  # Interval in seconds

    start_time = time.time()  # Record the start time

    print("Starting...")
    with open(txt_file, 'w') as txtfile:
        for i, line in enumerate(data_lines):
            txtfile.write(','.join(line) + '\n')
            
            # Calculate the expected next write time
            next_time = start_time + (i + 1) * interval
            sleep_time = next_time - time.time()
            
            if sleep_time > 0:
                time.sleep(sleep_time)

    print("Complete: All data has been written.")

if __name__ == "__main__":
    simulate_serial_data("LoggedData_CalInertialAndMag.csv", "live_data.txt")
