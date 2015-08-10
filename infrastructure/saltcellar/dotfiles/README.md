# Dotfile Extension

## Adding new functions, changing PATH/PYTHONPATH/etc

_Never_ add formula-specific changes to bash_profile_skeleton.sh or zsh_skeleton.zsh!

* Generic shell fragments should be added to `~[ec2-user, root]/.sh_fragments.d`.
* Things that rely on Bash syntax should go in `~[ec2-user, root]/.bash_profile.d`,
* ZSH-specific things should go into `~[ec2-user, root]/.zshrc.d`.
