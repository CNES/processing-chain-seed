#!/usr/bin/env cwl-runner
cwlVersion: v1.2
$namespaces:
  s: https://schema.org/
  js: https://json-schema.org/
$schemas:
- http://schema.org/version/latest/schemaorg-current-http.rdf
$graph:
- class: Workflow
  id: '#main'
  label: Sentinel-2 NDWI workflow
  doc: Downloads a Sentinel-2 L2A product and computes NDWI from its B3 and B8 bands.
  inputs:
    bucket_name:
      type: string
      doc: S3 bucket containing the Sentinel-2 product & config.
    l2a_path_s3_url:
      type: string
      doc: S3 path or prefix of the Sentinel-2 L2A product.
    conf_path_s3_url:
      type: string
      doc: S3 path or prefix of the configuration file.
    input_dir:
      type: string
      default: data/input
      doc: Directory (relative to the working directory) where the downloaded Sentinel-2 product is stored.
  outputs:
    processed_product:
      type: File
      outputSource: run_ndwi/ndwi_out
    processed_product_stac:
      type: File
      outputSource: run_ndwi/ndwi_stac_out
  steps:
    run_get_conf:
      run: '#retrieve_conf'
      in:
        bucket_name: bucket_name
        file_path: conf_path_s3_url
        input_dir: input_dir
      out: [s2_out]
    run_get_l2a:
      run: '#retrieve_s2'
      in:
        bucket_name: bucket_name
        file_path: l2a_path_s3_url
        input_dir: input_dir
      out: [s2_out]
    run_ndwi:
      run: '#run_ndwi_container'
      in:
        product: run_get_l2a/s2_out
        config: run_get_conf/s2_out
      out:
        - ndwi_out
        - ndwi_stac_out

- class: CommandLineTool
  id: retrieve_s2
  baseCommand: download_from_s3
  hints:
    DockerRequirement:
      dockerPull: artifactory.cnes.fr/platform-incub-docker-prod-local/cwl-processing/cwl_helpers:v1.4.6
  requirements:
    NetworkAccess:
      networkAccess: true
    InlineJavascriptRequirement: {}
  inputs:
    bucket_name:
      type: string
      inputBinding:
        prefix: "--bucket"
        position: 1
    file_path:
      type: string
      inputBinding:
        prefix: "--path"
        position: 2
    input_dir:
      type: string
      default: data/input
      inputBinding:
        prefix: "--out"
        valueFrom: $(runtime.outdir + "/" + self)
        position: 0
  outputs:
    s2_out:
      type: File
      outputBinding:
        glob: $(inputs.input_dir)/*

- class: CommandLineTool
  id: retrieve_conf
  baseCommand: download_from_s3
  hints:
    DockerRequirement:
      dockerPull: artifactory.cnes.fr/platform-incub-docker-prod-local/cwl-processing/cwl_helpers:v1.4.6
  requirements:
    NetworkAccess:
      networkAccess: true
    InlineJavascriptRequirement: {}
  inputs:
    bucket_name:
      type: string
      inputBinding:
        prefix: "--bucket"
        position: 1
    file_path:
      type: string
      inputBinding:
        prefix: "--path"
        position: 2
    input_dir:
      type: string
      default: data/input
      inputBinding:
        prefix: "--out"
        valueFrom: $(runtime.outdir + "/" + self)
        position: 0
  outputs:
    s2_out:
      type: File
      outputBinding:
        glob: $(inputs.input_dir)/*

- class: CommandLineTool
  id: '#run_ndwi_container'
  baseCommand: ["python3", "/app/compute_ndwi.py"]
  arguments:
    - --product
    - $(inputs.product.basename)
    - --output
    - .
    - --config
    - config.json
  requirements:
    DockerRequirement:
      dockerPull: cnes/processing-chain-seed:0.0.5
    ResourceRequirement:
      coresMin: 2
      coresMax: 2
      ramMin: 256
      ramMax: 3000
    InitialWorkDirRequirement:
      listing:
        - entryname: $(inputs.product.basename)
          entry: $(inputs.product)
        - entryname: config.json
          entry: $(inputs.config)
    InlineJavascriptRequirement: {}
  inputs:
    product:
      type: File
    config:
      type: File
  outputs:
    ndwi_out:
      type: File
      outputBinding:
        glob: "*L2B*.tif"
    ndwi_stac_out:
      type: File
      outputBinding:
        glob: "*L2B*.json"
