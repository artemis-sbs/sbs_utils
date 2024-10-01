set VERSION=v3.9.39

del sbs_utils_dev.sbslib
tar -caf sbs_utils_dev.zip --exclude="__pycache__" sbs_utils 
copy sbs_utils_dev.zip ..\__LIB__\artemis-sbs.sbs_utils.%VERSION%.sbslib
