# CUBES setup in this folder

This is the OutSystems CUBES source repository at commit `f458cc00`.
CUBES synthesizes a SQL query from example input tables and a desired output table.

## What was done

1. Cloned `https://github.com/OutSystems/CUBES.git` into `~/Experiments_cubes`.
2. Installed Miniconda into `.miniconda3`, keeping it local to this project.
3. Created the named `cubes` environment from the repository's `conda.txt`. The command uses only `conda-forge` because all pinned packages come from that channel and the unused default Anaconda channels require separate Terms of Service acceptance.
4. Installed the additional packages from the project README. The unpinned `z3-solver` selected a source release that failed to build, so `z3-solver==4.12.2.0` was installed as a prebuilt wheel. `sqlalchemy<2` was used for compatibility with this older project.
5. Verified Python 3.8.3, R 3.6.3, `rpy2` 3.3.2, and Z3 4.12.2, then ran the introductory example. It produced both an R and SQL solution.

The local Miniconda installation and its environments are excluded from Git by `.gitignore`.

## Run in the VS Code terminal

Open this folder in VS Code, then use **Terminal > New Terminal**:

```bash
cd ~/Experiments_cubes
./run-demo.sh
```

This activates the `cubes` Conda environment and runs the introductory example. The final `SQL Solution` section is the synthesized query. It counts students per course from the example tables and matches the desired output table.

To activate the environment manually:

```bash
cd ~/Experiments_cubes
source .miniconda3/etc/profile.d/conda.sh
conda activate cubes
```

To run another example:

```bash
cd ~/Experiments_cubes
source .miniconda3/etc/profile.d/conda.sh
conda activate cubes
python sequential.py tests-examples/55-tests/1.yaml
```

For parallel CUBES, start with two workers and the repository's recommended settings for two workers:

```bash
cd ~/Experiments_cubes
source .miniconda3/etc/profile.d/conda.sh
conda activate cubes
python cubes.py tests-examples/demo/intro.yaml -j 2 --no-split-complex-joins --probing-threads=1
```

Some benchmark examples take much longer than the introduction. Use `--help` on either Python script for all options.

## If the environment needs to be recreated

From this folder, run:

```bash
source .miniconda3/etc/profile.d/conda.sh
conda create --yes --name cubes --override-channels --channel conda-forge --file conda.txt
conda activate cubes
python -m pip install --only-binary=:all: z3-solver==4.12.2.0 psutil chromalog pylru frozendict 'sqlalchemy<2' libs/TestSuiteEval-1.0.3-py3-none-any.whl pebble
```

The upstream instructions are in [README.md](README.md), and the example inputs are in `tests-examples/`.
