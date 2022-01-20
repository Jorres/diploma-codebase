import os

for dirpath, dnames, fnames in os.walk("./new_sorts/"):
    for filename in fnames:
        n_outputs = -1
        full_filename = "./new_sorts/" + filename
        with open(full_filename, "r") as f:
            aig_header = f.readline().split(" ")
            print(aig_header)
            n_outputs = int(aig_header[2])

        with open(full_filename, "a") as f:
            for i in range(0, n_outputs):
                f.write("i{} v{}\n".format(i, i))
            for i in range(0, n_outputs):
                f.write("o{} o{}\n".format(i, i))
