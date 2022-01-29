import os
import subprocess
import aiger


def validate_aiger_dump_with_abc():
    dir_name = "aiger-abc-dump"

    for dirpath, dnames, fnames in os.walk(dir_name):
        for filename in fnames:
            if not filename.endswith("aag") or filename.startswith("dumped"):
                continue
            aig = aiger.load(f"{dirpath}/{filename}")

            dump_path = f"{dirpath}/dumped_{filename}"
            print(dump_path)

            # subprocess.call(f"touch {dump_path}")
            aig.write(dump_path)

# why rerunning generate_aigs does not work? find an obvious bug somewhere

validate_aiger_dump_with_abc()
