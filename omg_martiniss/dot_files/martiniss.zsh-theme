if [ "$USER" = "root" ]
then CARETCOLOR="red"
else CARETCOLOR="blue"
fi

MODE_INDICATOR="%{$fg_bold[red]%}>%{$fg[red]%}>>%{$reset_color%} "

function vi_mode_prompt_info() {
  # echo "${${KEYMAP/vicmd/$MODE_INDICATOR}/(main|viins)/idunno}"
  case $KEYMAP in
    vicmd) echo "%{$fg[red]%}NORMAL%{$reset_color%}" ;;
    viins) echo "%{$fg[blue]%}INSERT%{$reset_color%}" ;;
    main) echo "%{$fg[blue]%}INSERT%{$reset_color%}" ;;
    "") echo "%{$fg[blue]%}INSERT%{$reset_color%}" ;;
  esac
}

function zle-keymap-select() {
  zle reset-prompt
  zle -R
}

zle -N zle-keymap-select

local return_code="%(?..%{$fg[red]%}%? ↵%{$reset_color%})"

PROMPT='%{$reset_color%}%{${fg[green]}%}$($HOME/martiniss_scripts/title -currentPane $(pwd)) %{$reset_color%}:$(vi_mode_prompt_info): $(git_prompt_info)%{${fg_bold[$CARETCOLOR]}%}
=> %{${reset_color}%} '

RPS1='${return_code}'

ZSH_THEME_GIT_PROMPT_PREFIX="%{$fg_bold[cyan]%}‹"
ZSH_THEME_GIT_PROMPT_SUFFIX="› %{$reset_color%}"

# MODE_INDICATOR="%{$fg_bold[magenta]%}<%{$reset_color%}%{$fg[magenta]%}<<%{$reset_color%}"

# TODO use 265 colors
# MODE_INDICATOR="$FX[bold]$FG[020]<$FX[no_bold]%{$fg[blue]%}<<%{$reset_color%}"
# TODO use two lines if git
