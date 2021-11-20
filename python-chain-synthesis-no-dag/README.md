## Disclaimer

An explicit decision was made to not handle any runtime errors, UB's everywhere, use with care!

## Installation 

1. Create virtual environment (optional)
2. Run `pipx install -r requirements.txt`

## Usage

### Formatting input data

In the following snippet, `n` is the number of arguments of every function and `m` is the number
of functions. `m` blocks follow, each containing `2 ** n` lines, representing truth table of each 
of `m` functions. Truth tables are separated by blank lines. 

```
n m
BLANK
0  |         |
...| 2 ** n  |
1  |         |
BLANK        |
...          | m
BLANK        |
0  |         |
...| 2 ** n  |
1  |         |
```

### Run with a predefined input

In the following snippet, N is the maximum number of vertices a generated schema can contain. 

```
python app.py N /path/to/truthtables/file
```

### Run randomly-generated tests

In the following snippet, N is the maximum number of vertices a generated schema can contain, 
and M is the maximum number of functions a tester will attempt to generate.

```
python random_tester.py N M
```

### Run benchmark with a fixed test-suite

Fixed test-suite file consists of one or more of the following:
```
N M
<truthtable>
---
```
For example:
```
2 1
0
1
1
0
---
```

