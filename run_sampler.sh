#!/bin/bash

#SBATCH --time 48:00:00
#SBATCH --mem 64G
#SBATCH --nodes 1
#SBATCH --ntasks 1
#SBATCH --cpus-per-task 50
#SBATCH --job-name cl_sampler
#SBATCH --array=1 #-40 #Run 40 copies of the code = 400. samples
#SBATCH --partition cosma8-serial
#SBATCH --account dp270
#SBATCH --output /cosma8/data/dp270/dc-glas1/slurm-out/slurm-%A_%a.out

source ~/.bashrc
conda deactivate
conda activate hera_sim

SCRIPT="/cosma/home/dp270/dc-glas1/cl_sampler/cl_gibbs_sampler/cl_sampler.py"

echo $@

# set default output directory (will be overwritten if parsed as cmd-line arg)
output_dir="cl_sampler"    # <------ change the directory name here or in cmd-line
for arg in "$@"
do
    case $arg in 
        -dir=*)
        output_dir="${arg#*=}"
        shift
        ;;
    esac
done

export OMP_NUM_THREADS=1 
python -u $SCRIPT "$@" -dir="$output_dir" \
                       -nsamples=1 \
                       -data_seed=20 \
                       -prior_seed=30 \
                       -profile=false \
                       -tol=1e-07\
                       -maxiter=20000\
                       -lmax=4\
                       -nside=128\
                       -NLST=2\
                       -freq=400.\
                       -lst_start=0.\
                       -lst_end=8.\
                       -ant_dist=1.5\
                       -dish_dia=1.\
                       -cosmic_var=false \
                       -front_factor=0.1 \
                       -jobid=$SLURM_ARRAY_TASK_ID

# Save a copy of the shell script in the directory created by cl_sampler.py
if [ -d "/cosma8/data/dp270/dc-glas1/$output_dir" ]; then
    cp "$0" "/cosma8/data/dp270/dc-glas1/$output_dir/run_sampler.sh"
else
    echo "Error: output directory '$output_dir' does not exist"
    exit 1
fi
