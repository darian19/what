### Running the Pipeline
The pipeline can be run end-to-end via the driver script, or each individual step can be run independently.

#### Prerequisites
- Ensure the products repository dir is exported in PRODUCTS variable
- Run `$PRODUCTS/install-YOMP.sh <INSTALL_DIR> <SCRIPT_DIR>` where `<INSTALL_DIR>` is a valid folder on your `PYTHONPATH` and `<SCRIPT_DIR>` is a valid folder on your `PATH`
- `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` environment variables must be set
- Set `YOMP_HOME` to `$PRODUCTS/YOMP` to use your existing checkout
- When running locally, make to sure to set "BUILD_WORKSPACE" to one level above your
  products repository to avoid unnecessary cloning.  For example, if you cloned Products to ~/numenta/repositories/products, you would use:

    `export BUILD_WORKSPACE=~/numenta/repositories`
    ```
    e.g. numenta
            |
            |- repositories
                  |- products
                  |- nupic
    ```
- If pipeline does not find "BUILD_WORKSPACE" it will create one for you inside `WORKSPACE` as follows:
  `${WORKSPACE}/<guid/BUILD_NUMBER>`
- If neither `BUILD_WORKSPACE` nor `WORKSPACE` are defined, the pipeline will raise an exception
- Tools accept parameters through command line. Also, parameters can be specified with .json which can be passed as command line parameter(--pipeline-json). Each tool writes phase status in given .json file. Use --help option for each tool for more details for parameters.


#### Execution via driver
```bash
    ./YOMP-pipeline --trigger-pipeline YOMP --YOMP-remote <YOMP-remote> --YOMP-branch <branch-name>
      --sha <commit-sha-for-trigger-pipeline> --release-version <YOMP-version-number> --log <log-level>
```
##### Example
```bash
    ./YOMP-pipeline --trigger-pipeline YOMP --YOMP-remote YOMP@YOMPhub.com:<YOMPhub_username>/applications.YOMP
      --YOMP-branch pipeline-development  --sha 7f1c852c719ed6b8de4f8cda42f3e9a583564066 --release-version 1.0 --log debug
```
- Pass parameter via .json file
```
     python build.py --pipeline-json pipeline.json --log debug
```
  Find sample json products/YOMP/YOMP/pipeline/src/pipeline.json.template

  **NOTE**: Currently, only the individual tools accept pipeline JSON files.  The overall pipeline execution relies on the full set of parameters.
