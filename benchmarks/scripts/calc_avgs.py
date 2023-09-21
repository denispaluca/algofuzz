import pandas as pd
import glob

contractnames = ['001', '004', '005','008', '012', '013', '014', '015', '017', '018', '019', '025', 'AlgoTether', 'ExchangeToken']
fuzzers = ['Partial', 'Total']
drivers = ['COVERAGE', 'STATE', 'COMBINED']


def calc_avg(contract, fuzzer, driver):
    filename = f'{contract}_{fuzzer}Fuzzer_Driver.{driver}'
    # Step 1: Get a list of all CSV files in the current directory (or specify your path)
    file_paths = glob.glob(f'benchmarks/{filename}_*.csv')  # Adjust the path if your files are in a different directory


    dfs = list(map(lambda x: pd.read_csv(x, skiprows=6), file_paths))

    rows = list(map(lambda x: x.shape[0], dfs))
    smallest = min(rows)
    # Initialize a DataFrame to hold the sum of all cells with 0
    sum_df = pd.DataFrame(0, index=range(smallest), columns=dfs[0].columns)

    # Step 2: Read each CSV and accumulate the sum for each cell
    for df in dfs:
        sum_df += df

    # Step 3: Calculate the average for each cell
    average_df = sum_df / len(file_paths)

    average_df.round(decimals=2).to_csv(f'benchmarks/avgs/{contract}_{fuzzer}_{driver}.csv', index=False)


for contract in contractnames:
    for fuzzer in fuzzers:
        for driver in drivers:
            calc_avg(contract, fuzzer, driver)