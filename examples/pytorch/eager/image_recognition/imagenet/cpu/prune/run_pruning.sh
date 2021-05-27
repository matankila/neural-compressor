#!/bin/bash
set -x

function main {
  init_params "$@"
  run_tuning

}

# init params
function init_params {

  for var in "$@"
  do
    case $var in
      --topology=*)
          topology=$(echo $var |cut -f2 -d=)
      ;;
      --config=*)
          config=$(echo $var |cut -f2 -d=)
      ;;
      --output_model=*)
          output_model=$(echo $var |cut -f2 -d=)
      ;;
          
    esac
  done

}

# run_tuning
function run_tuning {
    python main.py \
           --topology=${topology} \
           --prune \
           --config=${config} \
           --pretrained \
           --output-model=${output_model}
}

main "$@"
