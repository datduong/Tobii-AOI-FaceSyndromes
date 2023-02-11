
import os,sys,re,pickle, time
from datetime import datetime
import numpy as np 

# ! make script to compare 2 groups on the same image. 
# ! may have 1 to 3 groups 

script_base = """#!/bin/bash

source /data/$USER/conda/etc/profile.d/conda.sh
conda activate py37

module load CUDA/11.0
module load cuDNN/8.0.3/CUDA-11.0
module load gcc/8.3.0

code_dir=/data/duongdb/Tobii-AOI-FaceSyndromes/aoi_segmentation
cd $code_dir

# ! 

main_data_dir=/data/duongdb/Face11CondTobiiEyeTrack01112023/RemoveAveEyeTrack

img_dir_group_1=$main_data_dir/SLIDE_NUM/GROUP1 
img_dir_group_2=$main_data_dir/SLIDE_NUM/GROUP2

output_dir=$main_data_dir/CompareGroupSameImgSLIDE_NUM # mean_vs_model.csv
mkdir $output_dir


# ! may as well do this at tons of threshold to see what happens

for this_k in 10 
do
  for this_thres in .1 
  do

    #  .35 .2 .3 .4 .45 .5 
    
    for cut_ave_img_to_binary in .25 
    do
    
    python3 apply_segmentation.py --cut_seg_to_binary_1 $this_thres --cut_seg_to_binary_2 $this_thres --img_dir_group_1 $img_dir_group_1 --img_dir_group_2 $img_dir_group_2 --output_dir $output_dir --resize 720 --k $this_k --plot_segmentation --boot_num 1000 --if_smoothing --scale_or_shift_ave_pixel .2 --cut_ave_img_to_binary $cut_ave_img_to_binary
    
    done 
    
  done
done 


"""

# ---------------------------------------------------------------------------- #

this_k = 10 # 20 # ! lower-->rough shape, higher-->more smooth
cut_seg_to_binary_1 = .5 # ! higher-->more white spot. lower-->less white spot
cut_seg_to_binary_2 = .5 

# ---------------------------------------------------------------------------- #

script_path = '/data/duongdb/Face11CondTobiiEyeTrack01112023'

main_folder = '/data/duongdb/Face11CondTobiiEyeTrack01112023/RemoveAveEyeTrack' # @main_folder is where we save all the data

slide_folders = os.listdir(main_folder) # @slide_folders should be "Slide1", "Slide2" ...

slide_folders = [s for s in slide_folders if ('Slide' in s) and ('CompareGroup' not in s)]

# slide_folders = ['Slide2','Slide11'] # , 'Slide3']

# ---------------------------------------------------------------------------- #

# ! for each slide1, slide2 (as a folder)
# ! for each group1, group2 ...

os.chdir(main_folder)

for folder in slide_folders: 
  for SUFFIX in ['Group']: # ,'OnSlide1']: 
    # if len(SUFFIX)>0: 
    group_folder = [f for f in os.listdir(folder) if re.match(r'^'+SUFFIX,f) ]
    # else: 
    #   group_folder = [f for f in os.listdir(folder) if 'OnSlide1' not in f] # kinda dumb... whatever
    #
		#
    group_folder = [g for g in group_folder if 'Result' not in g]
    group_folder = [g for g in group_folder if 'all' not in g]
    group_folder = [g for g in group_folder if os.path.isdir(os.path.join(main_folder,folder,g))]
    print (folder, group_folder)
		#
    for i,g1 in enumerate(group_folder):
      for j,g2 in enumerate(group_folder): 
        if j<=i: 
          continue
        print (g1,g2)
        if g1=='Group1' and g2=='Group3': 
          continue
        if g1=='Group1' and g2=='Group4': 
          continue
        # if g1=='Group2' and g2=='Group3': 
        #   continue
        # if g1=='Group2' and g2=='Group4': 
        #   continue
        # if g1=='Group1OnSlide1' and g2=='Group3OnSlide1': 
        #   continue
        # if g1=='Group1OnSlide1' and g2=='Group4OnSlide1': 
        #   continue
        # if g1=='Group2OnSlide1' and g2=='Group3OnSlide1': 
        #   continue
        # if g1=='Group2OnSlide1' and g2=='Group4OnSlide1': 
        #   continue
        #
        script = re.sub('THIS_K',str(this_k),script_base)
        script = re.sub('THRESHOLD_GROUP_1',str(cut_seg_to_binary_1),script)
        script = re.sub('THRESHOLD_GROUP_2',str(cut_seg_to_binary_2),script)
        script = re.sub('SLIDE_NUM',str(folder),script)
        script = re.sub('GROUP1',g1,script)
        script = re.sub('GROUP2',g2,script)
				#
        time.sleep( 1.5 )
        now = datetime.now() # current date and time
        script_name = os.path.join(script_path,'script'+'-'+now.strftime("%m-%d-%H-%M-%S")+'.sh')
        fout = open(script_name,'w')
        fout.write(script)
        fout.close()
        os.system('sbatch --time=00:35:00 --mem=4g --cpus-per-task=4 ' + script_name )
        # exit()
				
#



