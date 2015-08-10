# ----------------------------------------------------------------------
# Numenta Platform for Intelligent Computing (NuPIC)
# Copyright (C) 2015, Numenta, Inc.  Unless you have purchased from
# Numenta, Inc. a separate commercial license for this software code, the
# following terms and conditions apply:
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 3 as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see http://www.gnu.org/licenses.
#
# http://numenta.org/licenses/
# ----------------------------------------------------------------------
#
# .zshrc is sourced in interactive shells.
# It should contain commands to set up aliases,
# functions, options, key bindings, etc.

autoload -U compinit
compinit

#allow tab completion in the middle of a word
setopt COMPLETE_IN_WORD

## keep background processes at full speed
setopt NOBGNICE

## restart running processes on exit
#setopt HUP

# Set some sane history options
setopt append_history
setopt extended_history
setopt hist_expire_dups_first
setopt hist_ignore_all_dups
setopt hist_ignore_dups
setopt hist_ignore_space
setopt hist_reduce_blanks
setopt hist_save_no_dups
setopt hist_verify

# Share your history across all your terminal windows
setopt share_history

# Keep a ton of history.
HISTSIZE=10000
SAVEHIST=10000
HISTFILE=~/.zsh_history

export HISTIGNORE="ls:cd:cd -:pwd:exit:date"

## never ever beep ever
#setopt NO_BEEP

## automatically decide when to page a list of completions
#LISTMAX=0

## disable mail checking
#MAILCHECK=0

autoload -U colors
colors

# Set up prompt.

autoload -U promptinit
promptinit
prompt bart

# Set a sane $PATH
PATH=/opt/numenta/anaconda/bin
PATH="${PATH}:/usr/local/YOMP/bin"
PATH="${PATH}:/usr/local/bin"
PATH="${PATH}:/usr/local/sbin"
PATH="${PATH}:/usr/bin:/usr/sbin:/bin:/sbin"
export PATH

# Use anaconda PYTHONPATH
export PYTHONPATH=/opt/numenta/anaconda/lib/python2.7/site-packages

# Long running processes should return the time they took to run after they
# complete (specified in seconds)
REPORTTIME=2
TIMEFMT="'$fg[green]%J$reset_color' time: $fg[blue]%*Es$reset_color, cpu: $fg[blue]%P$reset_color"

# Make it easier for children of nta-nucleus to add things to .zshrc
#
# If you need to add a function, extend/change PATH or PYTHONPATH, add a file
# in ~/.sh_fragments.d. Files there will be sourced in alphanumeric order. If
# the fragment uses zsh-specific syntax, put it into ~/.zshrc.d

# Generic shell - fragments here should work in both bash and zsh
# Handle global shell fragments

# Check that there are fragment files first, otherwise we'll get a complaint
# about $dotfile not existing
if [ -n "$(ls /etc/.sh_fragments.d)" ]; then
  for dotfile in /etc/.sh_fragments.d/*
  do
    if [ -r "${dotfile}" ]; then
      source "${dotfile}"
    fi
  done
fi

# Handle account-specific shell fragments
mkdir -p ~/.sh_fragments.d
if [ -n "$(ls ~/.sh_fragments.d)" ]; then
  for dotfile in ~/.sh_fragments.d/*
  do
    if [ -r "${dotfile}" ]; then
      source "${dotfile}"
    fi
  done
fi

# ZSH specific fragment files go in ~/.zshrc.d
mkdir -p ~/.zshrc.d
if [ -n "$(ls ~/.zshrc.d)" ]; then
  for dotfile in ~/.zshrc.d/*
  do
    if [ -r "${dotfile}" ]; then
      source "${dotfile}"
    fi
  done
fi

# Don't leave the var hanging around the environment
unset dotfile

# Put any local changes in .sh_aliases, ~/.zshrc will be rewritten every Salt run.
if [ -f ~/.sh_aliases ]; then
  source ~/.sh_aliases
fi

# CentOS adds -i aliases. There's a reason it is an option and not POSIX
# default behavior. Disable.
REMOVE_CP_ALIAS=$(alias | grep -c 'cp -i')
if [ "${REMOVE_CP_ALIAS}" != 0 ]; then
  unalias cp
fi
REMOVE_MV_ALIAS=$(alias | grep -c 'mv -i')
if [ "${REMOVE_MV_ALIAS}" != 0 ]; then
  unalias mv
fi
REMOVE_RM_ALIAS=$(alias | grep -c 'rm -i')
if [ "${REMOVE_RM_ALIAS}" != 0 ]; then
  unalias rm
fi
unset REMOVE_CP_ALIAS
unset REMOVE_MV_ALIAS
unset REMOVE_RM_ALIAS

SSHkeylist=$(ssh-add -l 2>&1)
if [[ $? == "0" ]]; then
  echo
  echo "SSH keys:"
  echo "${SSHkeylist}"
fi
