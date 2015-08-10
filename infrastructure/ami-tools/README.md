# AMI-Tools

## Requirements
- bzip2
- [packer](https://www.packer.io/)
- [rake](https://rubygems.org/gems/rake)
- rsync
- wget

## Usage

`rake bake_YOMP_plumbing` - Generate a YOMP Plumbing AMI candidate (HVM, 32GB)
`rake bake_webserver` - Generate a webserver AMI candidate (HVM, 32GB)

## Notes:

* Any scratch files should be kept in the workspace directory.
* All packer configurations should be put in the `ami-configurations` directory.
* AMI-specific helper scripts should be named after the AMI and put in the packer-scripts directory. `cleanup-webserver-ami`, for example.
