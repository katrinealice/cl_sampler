#!/bin/bash

#SBATCH --time 72:00:00
#SBATCH --mem 64G
#SBATCH --nodes 1
#SBATCH --ntasks 1
#SBATCH --cpus-per-task 50
#SBATCH --job-name cl_sampler
#SBATCH --array=1 #-40 #Run 40 copies of the code = 400. samples
#SBATCH --output /nfs_perseus2/raid3/kglass/slurm-out/slurm-%A_%a.out

source ~/.bashrc
conda deactivate
conda activate hydra

SCRIPT="/home/kglass/cl_sampler/cl_gibbs_sampler/cl_sampler.py"
DATA="/home/kglass/data"
LOGFILE="$DATA/temp_output_$(date +%Y-%m-%d_%H-%M-%S).log"
SLURM_ARRAY_TASK_ID=0

echo $@

# set default output directory (will be overwritten if parsed as cmd-line arg)
output_dir="output"    # <------ change the directory name here or in cmd-line
prev=""
for arg in "$@"; do
    if [[ "$prev" == "-dir" ]]; then
        output_dir="$arg"
        prev=""
        continue
    fi
    case "$arg" in
        -dir=*) output_dir="${arg#*=}" ;;
        -dir) prev="-dir" ;;
    esac
done


export OMP_NUM_THREADS=1 
python -u $SCRIPT -dir="$output_dir" \
                  -nsamples=10000 \
                  -data_seed=20 \
                  -prior_seed=30 \
                  -profile=false \
                  -tol=5e-07\
                  -maxiter=30000\
                  -lmax=30\
                  -nside=128\
                  -NLST=10\
                  -freq=400.\
                  -freq_bounds="[400,500,10]"\
                  -lst_start=0.\
                  -lst_end=8.\
                  -dish_dia=1.\
		  -ant_dist=1.5\
                  -cl_sampling=true \
                  -include_wf=true \
                  -include_RSB=false \
                  -RSB_only=false \
                  -RSB_boost=1 \
                  -cosmic_var=false \
                  -front_factor=0.1 \
                  -zero_prior_mean=true \
                  -zero_inv_prior=false \
                  -cl_prior_pow=0. \
                  -noise_factor=1 \
                  -jobid=$SLURM_ARRAY_TASK_ID \
                  "$@" \
		  2>&1 | tee -a "$LOGFILE"

# move python output to correct folder
mv "$LOGFILE" "$DATA/$output_dir/output.log"

# Save a copy of the shell script in the directory created by cl_sampler.py
if [ -d "$DATA/$output_dir" ]; then
	cp "$0" "$DATA/$output_dir/run_sampler_$(date +%Y-%m-%d).sh"
else
    echo "Error: output directory '$output_dir' does not exist"
    exit 1
fi
