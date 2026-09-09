# processing-chain-seed (Sentinel-2 NDWI chain)

In order to help you to industrialize your processing chain this repository provides a simple example.

As algorithme example with used a simple processing chain that takes two Sentinel-2 bands as input (green
B03 and near-infrared B08 in GeoTIFF format) and produces an NDWI
(Normalized Difference Water Index) product as output, used to delineate
water surfaces (e.g. lake outline).

## Project structure

```
.
├── Dockerfile              # docker image for the processing chain
├── ndwi-config.json        # NDWI output configuration
├── requirements.txt        # Python dependencies
├── src/
│   └── compute_ndwi.py     # NDWI computation script
├── cwl/
│   ├── ndwi.cwl            # CWL description of the CommandLineTool
│   └── ndwi-job.yml        # example job file (inputs)
└── data/
    ├── input/              # Input data
    ├── output/             # Output data
```

## Getting Sentinel-2 bands

The script expects two single-band GeoTIFF files:
- `B03.tif`: green band
- `B08.tif`: near-infrared band (NIR)

These bands can be extracted from a Sentinel-2 L2A product (`.SAFE`
folder) downloaded from the [Copernicus Data Space Ecosystem](https://dataspace.copernicus.eu/).
Place them for example in a `data/` folder at the project root.

## Run python code
```powershell
python -m pip install -r requirements.txt
python src/compute_ndwi.py --product data/input/SENTINEL2B_20260829-104909-474_L2A_T31TDH_C_V4-0.zip --output data/output/ --config ndwi-config.json
```

## Build the Docker image

```powershell
docker build -t ndwi-processor:latest .
```

## Run the chain directly with Docker

```powershell
docker run --rm -v ${PWD}/data:/data -v ${PWD}:/cfg:ro cnes/processing-chain-seed:latest `
  --product /data/input/product.zip --output /data/output --config /cfg/ndwi-config.json
```

the same base name. Via CWL, both names are derived from the downloaded ZIP:
`--output` sets the output directory. Both file names are derived by the
Python script from the ZIP name: `L2A` is replaced by `L2B`, with `.tif` and
`.json` extensions respectively.

## Run the chain via CWL

The [cwl/ndwi.cwl](cwl/ndwi.cwl) file describes the workflow (download from
S3 + NDWI computation) and references the Docker image
`cnes/processing-chain-seed:0.0.1` (built in the previous step). The
devcontainer installs [cwltool](https://github.com/common-workflow-language/cwltool),
so after rebuilding the devcontainer, run:

```bash
cwltool --outdir data/output cwl/ndwi.cwl cwl/ndwi-job.yml
```

The S3 download steps (`retrieve_s2` and `retrieve_conf`) require the `S3_ENDPOINT_URL`,
`S3_ACCESS_KEY` and `S3_SECRET_KEY` environment variables. Pass them
through to the containers with `--preserve-entire-environment`:

```bash
cwltool --preserve-entire-environment --outdir data/output cwl/ndwi.cwl cwl/ndwi-job.yml
```

Job inputs (`bucket_name`, `l2a_path_s3_url`, `conf_path_s3_url`, `input_dir`)
can be adapted either by editing [cwl/ndwi-job.yml](cwl/ndwi-job.yml) or by
overriding them directly on the command line, e.g.:

```bash
cwltool \
  --preserve-entire-environment \
  --outdir data/output \
  cwl/ndwi.cwl \
  --bucket_name larath-bucket \
  --l2a_path_s3_url SENTINEL2B_20260829-104909-474_L2A_T31TDH_C_V4-0.zip \
  --conf_path_s3_url ndwi-config.json \
  --input_dir data/input \
```

`input_dir` only controls the path (relative to the step's own temporary
working directory) where the downloaded product and configuration are staged
before being passed to the NDWI step; it does not persist them under the
repository's `data/input/` folder. With `--outdir data/output`, only the
final workflow outputs are copied into `data/output/` once the run succeeds.
For example, `SENTINEL2B_..._L2A_...zip` produces
`SENTINEL2B_..._L2B_...tif` and `SENTINEL2B_..._L2B_...json`.

## Github Action build and push the image to CNES DockerHub

By default for each commit it will update the version cnes/processing-chain-seed:dev
If the commit is tagged it will create a version with the current tag

## Manualy Build and push the image to CNES DockerHub

```powershell
echo "$DOCKER_API_KEY" | docker login -u "$DOCKER_LOGIN" --password-stdin && docker build -t "cnes/processing-chain-seed:x.x.x" . && docker push "cnes/processing-chain-seed:x.x.x"
```



## Interpreting the result

NDWI is positive over water surfaces and negative over vegetation/soil.
To extract a lake outline, threshold the `ndwi.tif` raster (e.g.
`NDWI > 0`) then vectorize the resulting binary mask (e.g. with
`rasterio.features.shapes` or `gdal_polygonize.py`).