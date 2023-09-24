from glob import glob
import matplotlib.axes
import pandas as pd
import matplotlib.pyplot as plt

contracts = ['AlgoTether', 'ExchangeToken']
fuzzers = ['Partial', 'Total']
drivers = ['COVERAGE', 'STATE', 'COMBINED']
# Sample file list - replace with paths to your CSV files
def main():
    figure, axes = plt.subplots(2, 3, figsize=(12, 8))
    for i in range(2):
        for j in range(3):
            plot_range(axes[i][j], contracts[0], fuzzers[i], drivers[j])

    for ax, label in zip(axes[-1, :], drivers):  # Only the bottom row gets the x labels
        ax.set_xlabel(label)

# Setting y-labels
    for ax, label in zip(axes[:, 0], fuzzers):  # Only the first column gets the y labels
        ax.set_ylabel(label)

    plt.savefig(f'{contracts[0]}_range_trans.png')


def plot_range(plt: matplotlib.axes.Axes, contract, fuzzer, driver):
    files = glob(f'benchmarks/{contract}_{fuzzer}Fuzzer_Driver.{driver}_*.csv')

    dfs = [pd.read_csv(f, skiprows=6) for f in files]

    rows = list(map(lambda x: x.shape[0], dfs))
    i = rows.index(min(rows))
    common_time_col = 'call_count'  # replace with the name of your time column
    # Initialize a DataFrame to hold the sum of all cells with 0
    cp = lambda: dfs[i][[common_time_col]].copy()
    min_df = cp()
    max_df = cp()
    avg_df = cp()
    median_df = cp()

    # Calculate min, max, and average across all dataframes
    metric_col = " percent_covered"  # replace with the name of your metric column
    min_df[metric_col] = pd.concat([df[metric_col] for df in dfs], axis=1).min(axis=1)
    max_df[metric_col] = pd.concat([df[metric_col] for df in dfs], axis=1).max(axis=1)
    avg_df[metric_col] = pd.concat([df[metric_col] for df in dfs], axis=1).mean(axis=1)
    median_df[metric_col] = pd.concat([df[metric_col] for df in dfs], axis=1).median(axis=1)

    # Plot the data
    plt.fill_between(min_df[common_time_col], min_df[metric_col], max_df[metric_col], alpha=0.2, color='brown')
    plt.plot(avg_df[common_time_col], avg_df[metric_col], label='Average', color='brown')
    plt.plot(median_df[common_time_col], median_df[metric_col], label='Median', color='orange')
    plt.set_xscale('log')


main()