import os

dir_name = "./iscas_aags"
for dirpath, dnames, fnames in os.walk(dir_name):
    for filename in fnames:
        if not filename.endswith("aag"):
            continue
        n_outputs = -1
        full_filename = "{}/{}".format(dir_name, filename)

        lines = None
        print(filename)
        with open(full_filename, "r") as f:
            lines = f.readlines()
            aig_header = lines[0].split(" ")
            print(aig_header)
            n_inputs = int(aig_header[2])
            n_outputs = int(aig_header[4])

        first_meta_line = -1
        for id, line in enumerate(lines):
            if line.startswith('i'):
                first_meta_line = id
                break

        # assert first_meta_line != -1

        with open(full_filename, "w") as f:
            for line in lines[:first_meta_line]:
                f.write(line)
            for i in range(0, n_inputs):
                f.write("i{} v{}\n".format(i, i))
            for i in range(0, n_outputs):
                f.write("o{} o{}\n".format(i, i))
