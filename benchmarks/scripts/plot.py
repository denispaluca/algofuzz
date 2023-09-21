import pandas as pd
import matplotlib.pyplot as plt
contracts = ['AlgoTether', 'ExchangeToken']
fuzzers = ['Partial', 'Total']
drivers = ['COVERAGE', 'STATE', 'COMBINED']



def plot_contract(contract, key, ylabel):
    for f in fuzzers:
        for d in drivers:
            df = pd.read_csv(f'benchmarks/avgs/{contract}_{f}_{d}.csv')
            plt.plot(df[key], label=f'{f} {d}')

    plt.xscale('log')
    plt.xlabel("Call Count")
    plt.ylabel(ylabel)
    plt.legend()

    plt.savefig(f'{contract}_{key}.png')
    clearplt()


def clearplt():
    plt.figure().clear()
    plt.close()
    plt.cla()
    plt.clf()


for contract in contracts:
    plot_contract(contract, ' percent_covered', 'Percent Covered')