# Algorithm hyperparameters:

# How disbalanced a gate is allowed to be to enter any of the bucket
DISBALANCE_THRESHOLD = 0.02
# This one is best left between 10 and 15, 2 ^ BUCKET_SIZE tasks are solved
BUCKET_SIZE = 13
# Ideally, for every test there exists a perfect moment where we can stop
# adding domains into the cartesian product. But this is some reasonable
# threshold based on sorting tests
MAX_CARTESIAN_PRODUCT_SIZE = 100000
RANDOM_SAMPLE_SIZE = 10000
