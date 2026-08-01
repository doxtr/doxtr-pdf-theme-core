"""
Core Absolute Fallbacks.
These strings are ONLY injected if the child theme is broken or missing .tex_t files.
"""

DEFAULT_TITLE_STYLES = {
    'classic': r"attach boxed title to top left={xshift=0pt, yshift=0pt}, boxed title style={empty, left=1ex, right=0pt}"
}

DEFAULT_ADMONITION_STYLE = r"""
\newtcolorbox{ddadmonbox@<< admon_style_name >>}[2]{
    enhanced, breakable, sharp corners, frame hidden, 
    colback=white, coltitle=black, title={#2}
}
"""

DEFAULT_NEED_STYLE = r"""
\newtcolorbox{ddneedbox@<< need_style_name >>}[2]{
    enhanced, breakable, sharp corners, frame hidden, 
    colback=white, coltitle=black, title={#2}
}
"""

DEFAULT_CONTAINER_STYLE = r"""
\definecolor{ddconttitlefg<< c_name >>}{cmyk}{<< c_conf.title_color_cmyk >>}
\definecolor{ddconttitletextfg<< c_name >>}{cmyk}{<< c_conf.title_font_color_cmyk >>}
\definecolor{ddconticonfg<< c_name >>}{cmyk}{<< c_conf.title_icon_color_cmyk >>}
\definecolor{ddcontcontentfg<< c_name >>}{cmyk}{<< c_conf.content_font_color_cmyk >>}
\definecolor{ddcontcontentbg<< c_name >>}{cmyk}{<< c_conf.content_background_color_cmyk >>}

\expandafter\def\csname ddconticon<< c_name >>\endcsname{<% if c_conf.title_icon %>{<< c_conf.title_icon_font_size >>\color{ddconticonfg<< c_name >>}<< c_conf.title_icon >>}\hspace{0.5em}<% endif %>}

\tcbset{ddcontainerstyle<< c_name >>/.style={enhanced, breakable, parbox=false, before skip=1.5em plus 0.5em minus 0.5em, after skip=1.5em plus 0.5em minus 0.5em, colback=ddcontcontentbg<< c_name >>, coltext=ddcontcontentfg<< c_name >>, fontupper=<% if c_conf.content_font %>\fontspec{<< c_conf.content_font >>}<% endif %><< c_conf.content_font_size >>, <% if not c_conf.container_frame %>frame hidden, boxrule=0pt, <% else %>colframe=ddconttitlefg<< c_name >>!50!black, boxrule=1pt, <% endif %>boxsep=0.25em, left=0.5em, right=0.5em, <% if c_conf.match_text_width %>grow to left by=\dimexpr 0.75em+<% if c_conf.container_frame %>1pt<% else %>0pt<% endif %>\relax, grow to right by=\dimexpr 0.75em+<% if c_conf.container_frame %>1pt<% else %>0pt<% endif %>\relax, <% endif %>},ddcontainertitlestyle<< c_name >>/.style={fonttitle=<% if c_conf.title_font %>\fontspec{<< c_conf.title_font >>}<% endif %><< c_conf.title_font_size >>, coltitle=ddconttitletextfg<< c_name >>, colbacktitle=ddconttitlefg<< c_name >>, doxtr<< c_conf.title_style >>style<% if doxtr_style_requires_arg[c_conf.title_style] %>={ddconttitlefg<< c_name >>}<% endif %>}}

\newtcolorbox{ddcontainer<< c_name >>}[1][]{ddcontainerstyle<< c_name >>, #1}
"""

# --- ABSOLUTE FALLBACK FOR TABLES ---
DEFAULT_TABLE_STYLE = r"""
\usetikzlibrary{patterns, fadings}
\definecolor{ddtableheaderbg}{cmyk}{<< t_conf.header_background_color_cmyk >>}
\definecolor{ddtableheaderfg}{cmyk}{<< t_conf.header_font_color_cmyk >>}
\definecolor{sphinxTableRowColorOdd}{cmyk}{<< t_conf.row_color_odd_cmyk >>}
\definecolor{sphinxTableRowColorEven}{cmyk}{<< t_conf.row_color_even_cmyk >>}
\definecolor{ddconttitlefgtable}{cmyk}{<< t_conf.title_background_color_cmyk >>}
\definecolor{ddconttitletextfgtable}{cmyk}{<< t_conf.title_font_color_cmyk >>}
\definecolor{ddtablefademask}{cmyk}{<< t_conf.title_background_fade_mask_color_cmyk >>}
\colorlet{sphinxTableRowColor}{white}\colorlet{sphinxTableBorderColor}{black!30}
\renewcommand{\sphinxstyletheadfamily}{<% if t_conf.header_font %>\fontspec{<< t_conf.header_font >>}<% endif %><< t_conf.header_font_size >>\color{ddtableheaderfg}}
\setlength{\aboverulesep}{0pt}\setlength{\belowrulesep}{0pt}\setlength{\extrarowheight}{0.75ex}\arrayrulecolor{black!30}\def\sphinxtoprule{\arrayrulecolor{ddconttitlefgtable}\toprule\arrayrulecolor{black!30}}\def\sphinxmidrule{\arrayrulecolor{ddtableheaderbg}\midrule\arrayrulecolor{black!30}}\def\sphinxbottomrule{\arrayrulecolor{ddconttitlefgtable}\bottomrule\arrayrulecolor{black!30}}
<% if t_conf.title_style != 'classic' %>\tcbset{ddtabletitlestyle/.style={fonttitle=<% if t_conf.title_font %>\fontspec{<< t_conf.title_font >>}<% endif %><< t_conf.title_font_size >>,coltitle=ddconttitletextfgtable,colbacktitle=ddconttitlefgtable,doxtr<< t_conf.title_style >>style<% if doxtr_style_requires_arg[t_conf.title_style] %>={ddconttitlefgtable}<% endif %>}}\long\def\dd@makecaption@table#1#2{\begingroup\def\sphinxAtStartPar{\relax}\def\par{\relax}<% if t_conf.get('caption_position', 'side') in ['top', 'bottom'] %><% if t_conf.caption_position == 'top' %>\gdef\sphinxaftertopcaption{\vspace*{\dimexpr-\baselineskip-\dp\strutbox-\extrarowheight+<< t_conf.get('caption_top_offset', '-0.5ex') >>\relax}\nointerlineskip}%<% else %>\gdef\sphinxaftertopcaption{}\vskip\abovecaptionskip<% endif %>\begin{tcolorbox}[enhanced, breakable=false, empty, size=minimal, width=\linewidth, nobeforeafter, fontupper=\fontsize{1pt}{1pt}\selectfont, ddtabletitlestyle, title={\strut\rule{<< t_conf.title_text_offset >>}{0pt}#1: #2\rule{<< t_conf.title_text_offset >>}{0pt}\strut}]\end{tcolorbox}%\endgraf<% if t_conf.caption_position == 'top' %>\vskip\belowcaptionskip<% endif %><% else %>\gdef\sphinxaftertopcaption{\vskip\belowcaptionskip}%\Ifthispageodd{\begin{tikzpicture}[remember picture, overlay]\node[anchor=south west, outer sep=0pt, rotate=-90, inner sep=0pt] (captionbox) at (\linewidth, \dimexpr\baselineskip+1.0ex+\heavyrulewidth\relax) {\begin{tcolorbox}[enhanced, breakable=false, empty, size=minimal, width=12cm, nobeforeafter, ddtabletitlestyle, title={\strut\rule{<< t_conf.title_text_offset >>}{0pt}#1: #2\rule{<< t_conf.title_text_offset >>}{0pt}\strut}]\end{tcolorbox}};\draw[black!30, line width=\heavyrulewidth] (captionbox.north west) -- (captionbox.south west);\end{tikzpicture}}{\begin{tikzpicture}[remember picture, overlay]\node[anchor=north west, outer sep=0pt, rotate=-90, inner sep=0pt] (captionbox) at (0pt, \dimexpr\baselineskip+1.0ex+\heavyrulewidth\relax) {\begin{tcolorbox}[enhanced, breakable=false, empty, size=minimal, width=12cm, nobeforeafter, ddtabletitlestyle, title={\strut\rule{<< t_conf.title_text_offset >>}{0pt}#1: #2\rule{<< t_conf.title_text_offset >>}{0pt}\strut}]\end{tcolorbox}};\draw[black!30, line width=\heavyrulewidth] (captionbox.north west) -- (captionbox.south west);\end{tikzpicture}}<% endif %>\endgroup}\def\LT@makecaption#1#2#3{\LT@mcol\LT@cols {@{}p{\linewidth}@{}}{\begingroup\def\sphinxAtStartPar{\relax}\def\par{\relax}<% if t_conf.get('caption_position', 'side') in ['top', 'bottom'] %><% if t_conf.caption_position == 'top' %>\gdef\sphinxlongtablecapskipadjust{\dimexpr-\baselineskip-\dp\strutbox-\extrarowheight+<< t_conf.get('caption_top_offset', '-0.5ex') >>\relax}%<% else %>\gdef\sphinxlongtablecapskipadjust{0pt}%\vskip\abovecaptionskip<% endif %>\begin{tcolorbox}[enhanced, breakable=false, empty, size=minimal, width=\linewidth, nobeforeafter, fontupper=\fontsize{1pt}{1pt}\selectfont, ddtabletitlestyle, title={\strut\rule{<< t_conf.title_text_offset >>}{0pt}#1{#2: }#3\rule{<< t_conf.title_text_offset >>}{0pt}\strut}]\end{tcolorbox}%\endgraf<% if t_conf.caption_position == 'top' %>\vskip\belowcaptionskip<% endif %><% else %>\gdef\sphinxlongtablecapskipadjust{-\abovecaptionskip}%\Ifthispageodd{\begin{tikzpicture}[remember picture, overlay]\node[anchor=south west, outer sep=0pt, rotate=-90, inner sep=0pt] (captionbox) at (\linewidth, \dimexpr\baselineskip+1.0ex+\heavyrulewidth\relax) {\begin{tcolorbox}[enhanced, breakable=false, empty, size=minimal, width=12cm, nobeforeafter, ddtabletitlestyle, title={\strut\rule{<< t_conf.title_text_offset >>}{0pt}#1{#2: }#3\rule{<< t_conf.title_text_offset >>}{0pt}\strut}]\end{tcolorbox}};\draw[black!30, line width=\heavyrulewidth] (captionbox.north west) -- (captionbox.south west);\end{tikzpicture}}{\begin{tikzpicture}[remember picture, overlay]\node[anchor=north west, outer sep=0pt, rotate=-90, inner sep=0pt] (captionbox) at (0pt, \dimexpr\baselineskip+1.0ex+\heavyrulewidth\relax) {\begin{tcolorbox}[enhanced, breakable=false, empty, size=minimal, width=12cm, nobeforeafter, ddtabletitlestyle, title={\strut\rule{<< t_conf.title_text_offset >>}{0pt}#1{#2: }#3\rule{<< t_conf.title_text_offset >>}{0pt}\strut}]\end{tcolorbox}};\draw[black!30, line width=\heavyrulewidth] (captionbox.north west) -- (captionbox.south west);\end{tikzpicture}}\vspace*{-\baselineskip}\vspace*{-2.2ex}<% endif %>\endgroup}}<% else %><% if t_conf.title_fade_dots %>\def\ddTableFadeDotsCode{\pgfmathsetlengthmacro{\myoffset}{<< t_conf.title_text_offset >>}\pgfmathsetlengthmacro{\myfadeoffset}{<< t_conf.title_background_fade_length >>}<% if t_conf.title_background_fade_shape == 'triangle' %>\def\ddFadePath{($(captionbox.south east) + (0, \myoffset)$) -- ($(captionbox.north east) + (0, \myoffset)$) -- ($ (captionbox.south east)!0.5!(captionbox.north east) + (0, \myoffset - \myfadeoffset) $) -- cycle}<% else %>\def\ddFadePath{($(captionbox.south east) + (0, \myoffset)$) rectangle ($(captionbox.north east) + (0, \myoffset - \myfadeoffset)$)}<% endif %>\fill[ddconttitlefgtable] (captionbox.south west) rectangle ($(captionbox.north east) + (0, \myoffset)$);\fill[ddconttitlefgtable, path fading=south] \ddFadePath;\fill[pattern=crosshatch dots, pattern color=ddconttitlefgtable] \ddFadePath;\fill[ddtablefademask, path fading=north] \ddFadePath;}<% endif %>\long\def\dd@makecaption@table#1#2{\begingroup\def\sphinxAtStartPar{\relax}\def\par{\relax}<% if t_conf.get('caption_position', 'side') in ['top', 'bottom'] %><% if t_conf.caption_position == 'top' %>\gdef\sphinxaftertopcaption{\vspace*{\dimexpr-\dp\strutbox-\extrarowheight+<< t_conf.get('caption_top_offset', '-0.5ex') >>\relax}\nointerlineskip}%<% else %>\gdef\sphinxaftertopcaption{}\vskip\abovecaptionskip<% endif %>\noindent\begin{tikzpicture}\node[anchor=south west, outer sep=0pt, text opacity=0, inner sep=<< t_conf.title_padding >>, font=<% if t_conf.title_font %>\fontspec{<< t_conf.title_font >>}<% endif %><< t_conf.title_font_size >>] (captionbox) at (0,0) {\def\par{\endgraf}\begin{varwidth}{\linewidth}\raggedright\rule{<< t_conf.title_text_offset >>}{0pt}\strut #1: #2\strut\rule{<< t_conf.title_text_offset >>}{0pt}\end{varwidth}};\fill[ddconttitlefgtable] (captionbox.south west) rectangle (captionbox.north east);\node[anchor=south west, outer sep=0pt, text=ddconttitletextfgtable, inner sep=<< t_conf.title_padding >>, font=<% if t_conf.title_font %>\fontspec{<< t_conf.title_font >>}<% endif %><< t_conf.title_font_size >>] at (0,0) {\def\par{\endgraf}\begin{varwidth}{\linewidth}\raggedright\rule{<< t_conf.title_text_offset >>}{0pt}\strut #1: #2\strut\rule{<< t_conf.title_text_offset >>}{0pt}\end{varwidth}};<% if t_conf.caption_position == 'top' %>\draw[black!30, line width=\heavyrulewidth] (captionbox.south west) -- (captionbox.south east);<% else %>\draw[black!30, line width=\heavyrulewidth] (captionbox.north west) -- (captionbox.north east);<% endif %>\end{tikzpicture}%\endgraf<% if t_conf.caption_position == 'top' %>\vskip\belowcaptionskip<% endif %><% else %>\gdef\sphinxaftertopcaption{\vskip\belowcaptionskip}%\Ifthispageodd{\begin{tikzpicture}[remember picture, overlay]\node[anchor=south west, outer sep=0pt, rotate=-90, text opacity=0, inner sep=<< t_conf.title_padding >>, font=<% if t_conf.title_font %>\fontspec{<< t_conf.title_font >>}<% endif %><< t_conf.title_font_size >>] (captionbox) at (\linewidth, \dimexpr\baselineskip+1.0ex+\heavyrulewidth\relax) {\def\par{\endgraf}\begin{varwidth}{12cm}\raggedright\rule{<< t_conf.title_text_offset >>}{0pt}\strut #1: #2\strut\rule{<< t_conf.title_text_offset >>}{0pt}\end{varwidth}};<% if t_conf.title_fade_dots %>\ddTableFadeDotsCode<% else %>\fill[ddconttitlefgtable] (captionbox.south west) rectangle (captionbox.north east);<% endif %>\node[anchor=south west, outer sep=0pt, rotate=-90, text=ddconttitletextfgtable, inner sep=<< t_conf.title_padding >>, font=<% if t_conf.title_font %>\fontspec{<< t_conf.title_font >>}<% endif %><< t_conf.title_font_size >>] at (\linewidth, \dimexpr\baselineskip+1.0ex+\heavyrulewidth\relax) {\def\par{\endgraf}\begin{varwidth}{12cm}\raggedright\rule{<< t_conf.title_text_offset >>}{0pt}\strut #1: #2\strut\rule{<< t_conf.title_text_offset >>}{0pt}\end{varwidth}};\draw[black!30, line width=\heavyrulewidth] (captionbox.north west) -- (captionbox.south west);\end{tikzpicture}}{\begin{tikzpicture}[remember picture, overlay]\node[anchor=north west, outer sep=0pt, rotate=-90, text opacity=0, inner sep=<< t_conf.title_padding >>, font=<% if t_conf.title_font %>\fontspec{<< t_conf.title_font >>}<% endif %><< t_conf.title_font_size >>] (captionbox) at (0pt, \dimexpr\baselineskip+1.0ex+\heavyrulewidth\relax) {\def\par{\endgraf}\begin{varwidth}{12cm}\raggedright\rule{<< t_conf.title_text_offset >>}{0pt}\strut #1: #2\strut\rule{<< t_conf.title_text_offset >>}{0pt}\end{varwidth}};<% if t_conf.title_fade_dots %>\ddTableFadeDotsCode<% else %>\fill[ddconttitlefgtable] (captionbox.south west) rectangle (captionbox.north east);<% endif %>\node[anchor=north west, outer sep=0pt, rotate=-90, text=ddconttitletextfgtable, inner sep=<< t_conf.title_padding >>, font=<% if t_conf.title_font %>\fontspec{<< t_conf.title_font >>}<% endif %><< t_conf.title_font_size >>] at (0pt, \dimexpr\baselineskip+1.0ex+\heavyrulewidth\relax) {\def\par{\endgraf}\begin{varwidth}{12cm}\raggedright\rule{<< t_conf.title_text_offset >>}{0pt}\strut #1: #2\strut\rule{<< t_conf.title_text_offset >>}{0pt}\end{varwidth}};\draw[black!30, line width=\heavyrulewidth] (captionbox.north west) -- (captionbox.south west);\end{tikzpicture}}<% endif %>\endgroup}\def\LT@makecaption#1#2#3{\LT@mcol\LT@cols {@{}p{\linewidth}@{}}{\begingroup\def\sphinxAtStartPar{\relax}\def\par{\relax}<% if t_conf.get('caption_position', 'side') in ['top', 'bottom'] %><% if t_conf.caption_position == 'top' %>\gdef\sphinxlongtablecapskipadjust{\dimexpr-\dp\strutbox-\extrarowheight+<< t_conf.get('caption_top_offset', '-0.5ex') >>\relax}%<% else %>\gdef\sphinxlongtablecapskipadjust{0pt}%\vskip\abovecaptionskip<% endif %>\noindent\begin{tikzpicture}\node[anchor=south west, outer sep=0pt, text opacity=0, inner sep=<< t_conf.title_padding >>, font=<% if t_conf.title_font %>\fontspec{<< t_conf.title_font >>}<% endif %><< t_conf.title_font_size >>] (captionbox) at (0,0) {\def\par{\endgraf}\begin{varwidth}{\linewidth}\raggedright\rule{<< t_conf.title_text_offset >>}{0pt}\strut #1{#2: }#3\strut\rule{<< t_conf.title_text_offset >>}{0pt}\end{varwidth}};\fill[ddconttitlefgtable] (captionbox.south west) rectangle (captionbox.north east);\node[anchor=south west, outer sep=0pt, text=ddconttitletextfgtable, inner sep=<< t_conf.title_padding >>, font=<% if t_conf.title_font %>\fontspec{<< t_conf.title_font >>}<% endif %><< t_conf.title_font_size >>] at (0,0) {\def\par{\endgraf}\begin{varwidth}{\linewidth}\raggedright\rule{<< t_conf.title_text_offset >>}{0pt}\strut #1{#2: }#3\strut\rule{<< t_conf.title_text_offset >>}{0pt}\end{varwidth}};\end{tikzpicture}%\endgraf<% if t_conf.caption_position == 'top' %>\vskip\belowcaptionskip<% endif %><% else %>\gdef\sphinxlongtablecapskipadjust{-\abovecaptionskip}%\Ifthispageodd{\begin{tikzpicture}[remember picture, overlay]\node[anchor=south west, outer sep=0pt, rotate=-90, text opacity=0, inner sep=<< t_conf.title_padding >>, font=<% if t_conf.title_font %>\fontspec{<< t_conf.title_font >>}<% endif %><< t_conf.title_font_size >>] (captionbox) at (\linewidth, \dimexpr\baselineskip+1.0ex+\heavyrulewidth\relax) {\def\par{\endgraf}\begin{varwidth}{12cm}\raggedright\rule{<< t_conf.title_text_offset >>}{0pt}\strut #1{#2: }#3\strut\rule{<< t_conf.title_text_offset >>}{0pt}\end{varwidth}};<% if t_conf.title_fade_dots %>\ddTableFadeDotsCode<% else %>\fill[ddconttitlefgtable] (captionbox.south west) rectangle (captionbox.north east);<% endif %>\node[anchor=south west, outer sep=0pt, rotate=-90, text=ddconttitletextfgtable, inner sep=<< t_conf.title_padding >>, font=<% if t_conf.title_font %>\fontspec{<< t_conf.title_font >>}<% endif %><< t_conf.title_font_size >>] at (\linewidth, \dimexpr\baselineskip+1.0ex+\heavyrulewidth\relax) {\def\par{\endgraf}\begin{varwidth}{12cm}\raggedright\rule{<< t_conf.title_text_offset >>}{0pt}\strut #1{#2: }#3\strut\rule{<< t_conf.title_text_offset >>}{0pt}\end{varwidth}};\draw[black!30, line width=\heavyrulewidth] (captionbox.north west) -- (captionbox.south west);\end{tikzpicture}}{\begin{tikzpicture}[remember picture, overlay]\node[anchor=north west, outer sep=0pt, rotate=-90, text opacity=0, inner sep=<< t_conf.title_padding >>, font=<% if t_conf.title_font %>\fontspec{<< t_conf.title_font >>}<% endif %><< t_conf.title_font_size >>] (captionbox) at (0pt, \dimexpr\baselineskip+1.0ex+\heavyrulewidth\relax) {\def\par{\endgraf}\begin{varwidth}{12cm}\raggedright\rule{<< t_conf.title_text_offset >>}{0pt}\strut #1{#2: }#3\strut\rule{<< t_conf.title_text_offset >>}{0pt}\end{varwidth}};<% if t_conf.title_fade_dots %>\ddTableFadeDotsCode<% else %>\fill[ddconttitlefgtable] (captionbox.south west) rectangle (captionbox.north east);<% endif %>\node[anchor=north west, outer sep=0pt, rotate=-90, text=ddconttitletextfgtable, inner sep=<< t_conf.title_padding >>, font=<% if t_conf.title_font %>\fontspec{<< t_conf.title_font >>}<% endif %><< t_conf.title_font_size >>] at (0pt, \dimexpr\baselineskip+1.0ex+\heavyrulewidth\relax) {\def\par{\endgraf}\begin{varwidth}{12cm}\raggedright\rule{<< t_conf.title_text_offset >>}{0pt}\strut #1{#2: }#3\strut\rule{<< t_conf.title_text_offset >>}{0pt}\end{varwidth}};\draw[black!30, line width=\heavyrulewidth] (captionbox.north west) -- (captionbox.south west);\end{tikzpicture}}\vspace*{-\baselineskip}\vspace*{-2.2ex}<% endif %>\endgroup}}<% endif %>
"""

# --- ABSOLUTE FALLBACK FOR FIGURES ---
DEFAULT_FIGURE_STYLE = r"""
\definecolor{ddfigcaptionbg}{cmyk}{<< f_conf.caption_background_color_cmyk >>}
\definecolor{ddfigcaptionfg}{cmyk}{<< f_conf.caption_font_color_cmyk >>}

\makeatletter
\long\def\dd@makecaption@figure#1#2{%
  \vskip\abovecaptionskip
  \begin{tcolorbox}[
    enhanced,
    frame hidden,
    boxrule=0pt,
    colback=ddfigcaptionbg,
    coltext=ddfigcaptionfg,
    arc=2pt,
    boxsep=0pt,
    left=<< f_conf.caption_padding >>, 
    right=<< f_conf.caption_padding >>, 
    top=<< f_conf.caption_padding >>, 
    bottom=<< f_conf.caption_padding >>,
    halign=<< f_conf.caption_align >>
  ]
  <% if f_conf.caption_font %>\fontspec{<< f_conf.caption_font >>}<% endif %><< f_conf.caption_font_size >>#1: #2
  \end{tcolorbox}%
  \vskip\belowcaptionskip
}
\makeatother
"""

# --- ABSOLUTE FALLBACK FOR SIDEBARS ---
DEFAULT_SIDEBAR_STYLE = r"""
\usepackage{wrapfig}

\definecolor{ddsidebartitlebg}{cmyk}{<< s_conf.title_background_color_cmyk >>}
\definecolor{ddsidebartitlefg}{cmyk}{<< s_conf.title_font_color_cmyk >>}
\definecolor{ddsidebariconfg}{cmyk}{<< s_conf.title_icon_color_cmyk >>}
\definecolor{ddsidebarcontentbg}{cmyk}{<< s_conf.content_background_color_cmyk >>}
\definecolor{ddsidebarcontentfg}{cmyk}{<< s_conf.content_font_color_cmyk >>}
\definecolor{ddsidebarborder}{cmyk}{<< s_conf.border_color_cmyk >>}
\definecolor{ddsidebarsubtitlefg}{cmyk}{<< s_conf.subtitle_font_color_cmyk >>}

\makeatletter
\renewenvironment{sphinxsidebar}{%
  \begin{wrapfigure}{<< s_conf.float_position >>}{<< s_conf.width >>}%
  \begin{minipage}{\linewidth}%
  \begin{tcolorbox}[enhanced, parbox=false, sharp corners, colback=ddsidebarcontentbg, coltext=ddsidebarcontentfg, colframe=ddsidebarborder, boxrule=<< s_conf.border_width >>, fontupper=<< s_conf.content_font_size >>, boxsep=0pt, left=0.75em, right=0.75em, top=0pt, bottom=0.5em, before skip=0pt, after skip=0pt]%
}{%
  \end{tcolorbox}%
  \end{minipage}%
  \end{wrapfigure}%
}
\renewcommand*\sphinxstylesidebartitle[1]{%
  \noindent\kern-0.75em\relax
  \begingroup
  \colorbox{ddsidebartitlebg}{%
    \hspace*{0.75em}%
    \parbox{\dimexpr\linewidth-0.75em\relax}{%
      \vskip 0.6em\relax
      << s_conf.title_font_size >>\color{ddsidebartitlefg}#1%
      \vskip 0.5em\relax
    }%
  }%
  \endgroup
  \par\nobreak\vskip 0.5em\relax
}
\renewcommand*\sphinxstylesidebarsubtitle[1]{%
  \begingroup\leftskip=0.75em\rightskip=0.75em
  \sphinxAtStartPar{\color{ddsidebarsubtitlefg}<< s_conf.subtitle_font_size >>#1}\par\medskip
  \endgroup
}
\makeatother
"""

# --- ABSOLUTE FALLBACK FOR HIGHLIGHTS ---
DEFAULT_HIGHLIGHTS_STYLE = r"""
\definecolor{ddhighlightstitlefg}{cmyk}{0,0.24,0.86,0.45}
\definecolor{ddhighlightscontentbg}{cmyk}{0,0.02,0.14,0}
\definecolor{ddhighlightscontentfg}{cmyk}{0.0,0.0,0.0,0.82}
\definecolor{ddhighlightsborder}{cmyk}{0,0.24,0.86,0.45}

\newtcolorbox{ddhighlightsbox}{
    enhanced, breakable, parbox=false,
    sharp corners,
    before skip=1.5em plus 0.5em minus 0.5em,
    after skip=1.5em plus 0.5em minus 0.5em,
    colback=ddhighlightscontentbg,
    coltext=ddhighlightscontentfg,
    colframe=ddhighlightsborder,
    boxrule=0pt,
    leftrule=3pt,
    toprule=0pt, rightrule=0pt, bottomrule=0pt,
    left=1em, right=1em, top=2.5em, bottom=1em,
    overlay unbroken and first={
        \node[anchor=north west, inner sep=0pt] at ([xshift=1em, yshift=-0.8em]frame.north west) {%
            {\large\bfseries\color{ddhighlightstitlefg}Highlights}%
        };
    },
}
"""

# --- ABSOLUTE FALLBACK FOR CODE BLOCKS ---
DEFAULT_CODE_STYLE = r"""
\makeatletter
\sphinxsetup{verbatimwithframe=false, verbatimsep=0pt}
\renewcommand{\sphinxVerbatim@FrameCommand}[1]{#1}

\providecommand{\ddCurrentCodeLang}{generic}

<% for lang, conf in doxtr_code.items() %>
\definecolor{ddcodebg_<< lang >>}{cmyk}{<< conf.content_background_color_cmyk >>}
\definecolor{ddcodefg_<< lang >>}{cmyk}{<< conf.content_font_color_cmyk >>}
\definecolor{ddcodetitlebg_<< lang >>}{cmyk}{<< conf.title_background_color_cmyk >>}
\definecolor{ddcodetitlefg_<< lang >>}{cmyk}{<< conf.title_font_color_cmyk >>}
\definecolor{ddcodeborder_<< lang >>}{cmyk}{<< conf.border_color_cmyk >>}
\definecolor{ddcodeicon_<< lang >>}{cmyk}{<< conf.icon_color_cmyk >>}

\expandafter\def\csname ddIconCommand<< lang >>\endcsname{<< conf.icon >>}

<% set title_parts = [] %>
<% if conf.show_mac_dots and conf.icon and conf.icon_position == 'before_mac_dots' %>
  <% set dummy = title_parts.append('\csname ddIconCommand' ~ lang ~ '\endcsname') %>
  <% set dummy = title_parts.append('\\hspace{0.8em}') %>
  <% set dummy = title_parts.append('\\tikz[baseline=-0.6ex]{\\fill[red!80!white] (0,0) circle (3pt); \\fill[yellow!80!black] (1em,0) circle (3pt); \\fill[green!80!black] (2em,0) circle (3pt);}') %>
<% elif conf.show_mac_dots and conf.icon %>
  <% set dummy = title_parts.append('\\tikz[baseline=-0.6ex]{\\fill[red!80!white] (0,0) circle (3pt); \\fill[yellow!80!black] (1em,0) circle (3pt); \\fill[green!80!black] (2em,0) circle (3pt);}') %>
  <% set dummy = title_parts.append('\\hspace{0.8em}') %>
  <% set dummy = title_parts.append('\csname ddIconCommand' ~ lang ~ '\endcsname') %>
<% elif conf.show_mac_dots %>
  <% set dummy = title_parts.append('\\tikz[baseline=-0.6ex]{\\fill[red!80!white] (0,0) circle (3pt); \\fill[yellow!80!black] (1em,0) circle (3pt); \\fill[green!80!black] (2em,0) circle (3pt);}') %>
<% elif conf.icon %>
  <% set dummy = title_parts.append('\csname ddIconCommand' ~ lang ~ '\endcsname') %>
<% endif %>

<% if title_parts|length > 0 %><% set dummy = title_parts.append('\\hspace{0.8em}') %><% endif %>

<% if conf.language_label %>
  <% set dummy = title_parts.append(conf.language_label) %>
<% else %>
  <% set dummy = title_parts.append('\\ifx\\ddCurrentCodeCaption\\empty\\MakeUppercase{\\ddCurrentCodeLang}\\else\\@ifundefined{c@ddlisting}{}{\\ifnum\\value{ddlisting}>0\\relax Listing \\theddlisting: \\fi}\\ddCurrentCodeCaption\\fi') %>
<% endif %>

\tcbset{doxtrcodestyle<< lang >>/.style={colback=ddcodebg_<< lang >>, coltext=ddcodefg_<< lang >>, colframe=ddcodeborder_<< lang >>, colbacktitle=ddcodetitlebg_<< lang >>, coltitle=ddcodetitlefg_<< lang >>, boxrule=<< conf.border_width >>, fontupper=<% if conf.content_font %>\fontspec{<< conf.content_font >>}<% endif %><< conf.content_font_size >>, fonttitle=<% if conf.title_font %>\fontspec{<< conf.title_font >>}<% endif %><< conf.title_font_size >>, title={\vspace*{0.1ex}<< title_parts | join('') >>}}}
<% endfor %>

\tcolorboxenvironment{sphinxVerbatim}{enhanced, breakable, sharp corners=south, rounded corners=north, arc=4pt, boxsep=0pt, left=1em, right=1em, top=0.5em, bottom=0.5em, toptitle=0.5ex, bottomtitle=0.5ex, doxtrcodestylegeneric, doxtrcodestyle\ddCurrentCodeLang/.try}

% Neutralize framed.sty's \MakeFramed inside sphinxVerbatim: tcolorbox handles
% all framing and page-breaking via the breakable option above.
% This hook fires AFTER tcolorboxenvironment's hook (which opens the tcolorbox),
% so the redefinitions are local to the tcolorbox group and auto-restore on close.
\def\dd@NeutralMakeFramed#1{\@tempdima\z@\let\width\@tempdima #1}
\AddToHook{env/sphinxVerbatim/before}{%
    \let\MakeFramed\dd@NeutralMakeFramed
    \def\endMakeFramed{}%
}

\makeatother
"""