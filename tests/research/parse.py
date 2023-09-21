import json
import os

from json import encoder
encoder.FLOAT_REPR = lambda o: format(o, '.2f')

fuzzers = ['PartialFuzzer', 'TotalFuzzer']
drivers = ['COVERAGE', 'STATE', 'COMBINED']

def main():
    reps = 10
    half_hour = 30 * 60
    # evaluate_contract(AlgoTether, half_hour, 1)
    #evaluate_contract(ExchangeToken, half_hour, reps)

    modules = ['AlgoTether']

    data = {}
    big_avg = [0 for _ in range(7)]
    for fuzzer in fuzzers:
        data[fuzzer] = {}
        fuzz_avg = [0 for _ in range(7)]
        for driver in drivers:
            tot_avg = [0 for _ in range(7)]
            for module in modules:
                name = f"{module}_{fuzzer}_Driver.{driver}"


                avgs = [0 for _ in range(7)]
                for i in range(reps):
                    last_line = read_n_to_last_line(f"./benchmarks/{name}_{i}.csv")
                    splitted = last_line.split(', ')
                    nums = [float(splitted[i]) for i in range(7)]
                    for j in range(7):
                        avgs[j] += nums[j]
                
                for j in range(7):
                    avgs[j] /= reps
                    tot_avg[j] += avgs[j]
            
            for j in range(7):
                tot_avg[j] /= len(modules)
                fuzz_avg[j] += tot_avg[j]

            data[fuzzer][driver] = tot_avg

        for j in range(7):
            fuzz_avg[j] /= len(drivers)
            big_avg[j] += fuzz_avg[j]

        data[fuzzer]['AVG'] = fuzz_avg
    
    for j in range(7):
        big_avg[j] /= len(fuzzers)

    data['AVG'] = big_avg

        
    txt = json.dumps(json.loads(json.dumps(data), parse_float=lambda x: round(float(x), 2)), indent=2)
    with open('benchmarks/eval-algot/avgs.json', 'w') as f:
        f.write(txt)

def get_verismart_modules():
    dir = os.path.dirname(__file__)
    verismart = os.path.join(dir, "algorand_veriSmart")
    onlyfiles = [
        f.replace(".py", "")
        for f in os.listdir(verismart)
        if os.path.isfile(file := os.path.join(verismart, f))
    ]
    onlyfiles.sort()
    return onlyfiles


def read_n_to_last_line(filename, n = 1):
    """Returns the nth before last line of a file (n=1 gives last line)"""
    num_newlines = 0
    with open(filename, 'rb') as f:
        try:
            f.seek(-2, os.SEEK_END)    
            while num_newlines < n:
                f.seek(-2, os.SEEK_CUR)
                if f.read(1) == b'\n':
                    num_newlines += 1
        except OSError:
            f.seek(0)
        last_line = f.readline().decode()
    return last_line

if __name__ == "__main__":
    main()
