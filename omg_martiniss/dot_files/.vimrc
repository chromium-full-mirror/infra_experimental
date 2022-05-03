set nocompatible

"======================"
" Vundle configuration "
"======================"

filetype off
set rtp+=~/.vim/bundle/Vundle.vim
if isdirectory(expand('$HOME/.vim/bundle/Vundle.vim'))
  call vundle#begin()
  " Required
  Plugin 'gmarik/vundle'

  Plugin 'easymotion/vim-easymotion'
  Plugin 'google/vim-colorscheme-primary'
  Plugin 'kien/ctrlp.vim'
  Plugin 'scrooloose/nerdcommenter'
  Plugin 'scrooloose/nerdtree'
  "Plugin 'scrooloose/syntastic'
  Plugin 'tpope/vim-fugitive'
  Plugin 'tpope/vim-surround'
  Plugin 'tpope/vim-sensible'
  Plugin 'tpope/vim-repeat'
  Plugin 'Yggdroot/indentLine'
  Plugin 'Valloric/MatchTagAlways'
  Plugin 'vim-scripts/netrw.vim'
  Plugin 'fatih/vim-go'
  Plugin 'altercation/vim-colors-solarized'
  Plugin 'encody/nvim'
  Plugin 'cappyzawa/starlark.vim'
  call vundle#end()
else
  echomsg 'Vundle is not installed. You can install Vundle from'
      \ 'https://github.com/VundleVim/Vundle.vim'
endif

" Load the default google configuration
source /usr/share/vim/google/google.vim

filetype on
filetype plugin on
filetype plugin indent on

"===================="
" Some basic options "
"===================="

" Enable syntax highlighting
syntax on
syntax enable
set t_Co=256

set background=dark
colorscheme primary

autocmd FileType starlark setlocal shiftwidth=2 softtabstop=2 expandtab

" Uncomment if you want to map ; to : to cut down on chording
" nnoremap ; :

" Automatically change the working path to the path of the current file
autocmd BufNewFile,BufEnter * silent! lcd %:p:h

" Show line numbers
set number

" use » to mark Tabs and ° to mark trailing whitespace. This is a
" non-obtrusive way to mark these special characters.
set list listchars=tab:»\ ,trail:°

" Highlight the search term when you search for it.
set hlsearch

" By default, it looks up man pages for the word under the cursor, which isn't
" very useful, so we map it to something else.
nnoremap <s-k> <CR>

" Explicitly set the Leader to comma. You you can use '\' (the default),
" or anything else (some people like ';').
let mapleader=','

"==================================="
" Load and Configure Google Plugins "
"==================================="
" For more plugins, see go/vim/plugins

" Loads youcompleteme, the awesomest autocompletion engine.
" See go/ycm for more details.
Glug youcompleteme-google
nnoremap <leader>d :YcmCompleter GoTo<CR>
let g:ycm_filetype_blacklist = {'cpp': 1, 'c': 1}
let g:go_disable_autoinstall = 1
let g:go_gocode_bin = 'gocode'

Glug codefmt gofmt_executable="goimports"
Glug codefmt-google
autocmd FileType go AutoFormatBuffer gofmt

" Wrap autocmds inside an augroup to protect against reloading this script.
" For more details, see:
" http://learnvimscriptthehardway.stevelosh.com/chapters/14.html
augroup autoformat
  autocmd BufRead,BufNewFile *.py set foldmethod=indent
  autocmd BufRead,BufNewFile *.go set tabstop=2
  autocmd BufRead,BufNewFile *.cfg set syntax=python
  autocmd BufRead,BufNewFile *.pyl set syntax=python
  autocmd BufRead,BufNewFile *.pyl set expandtab
augroup END


nnoremap <leader>ga :Git add %:p<CR><CR>
nnoremap <leader>gs :Gstatus<CR>
nnoremap <leader>gc :Gcommit -v -q<CR>
nnoremap <leader>gt :Gcommit -v -q %:p<CR>
nnoremap <leader>gd :Gdiff<CR>
nnoremap <leader>ge :Gedit<CR>
nnoremap <leader>gr :Gread<CR>
nnoremap <leader>gw :Gwrite<CR><CR>
nnoremap <leader>gl :silent! Glog<CR>:bot copen<CR>
nnoremap <leader>gp :Ggrep<Space>
nnoremap <leader>gm :Gmove<Space>
nnoremap <leader>gb :Git branch<Space>
nnoremap <leader>go :Git checkout<Space>
nnoremap <leader>gps :Dispatch! git push<CR>
nnoremap <leader>gpl :Dispatch! git pull<CR>

nnoremap <leader>p :CtrlPMixed<CR>

nnoremap <leader>b :TagbarToggle<CR>

let g:ctrlp_user_command = '/usr/bin/ag %s -i --nocolor --nogroup --hidden
      \ --ignore .git
      \ --ignore .svn
      \ --ignore .hg
      \ --ignore .DS_Store
      \ --ignore "**/*.pyc"
      \ --ignore .git5_specs
      \ --ignore review
      \ -g ""'

set foldmethod=syntax
set colorcolumn=80
set completeopt=menuone
set tabstop=2
inoremap ;; <Esc>

let g:go_highlight_functions = 1
let g:go_highlight_methods = 1
let g:go_highlight_fields = 1
let g:go_highlight_types = 1
let g:go_highlight_operators = 1
let g:go_highlight_build_constraints = 1
let g:syntastic_go_checkers = ['golint', 'govet', 'errcheck']
let g:syntastic_mode_map = { 'mode': 'active', 'passive_filetypes': ['go'] }

" syntastic stuff
" set statusline+=%#warningmsg#
" set statusline+=%{SyntasticStatuslineFlag()}
" set statusline+=%*
" let g:syntastic_always_populate_loc_list = 1
" let g:syntastic_auto_loc_list = 1
" let g:syntastic_check_on_open = 1
" let g:syntastic_check_on_wq = 0

nnoremap )e :lnext<CR>
nnoremap (e :lprevious<CR>

vnoremap <leader>/ y/<C-R>"<CR>

"let g:instant_markdown_autostart = 0


" GUI font stuff
set guifont=Noto\ Mono\ 14

:nmap <F1> :echo<CR>
