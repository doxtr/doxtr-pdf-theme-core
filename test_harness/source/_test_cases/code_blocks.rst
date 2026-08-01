.. _test_code_blocks:

Showing Code
============

This chapter demonstrates the per-language code block styling system.
Each language gets a unique color palette and icon — either from FontAwesome
brand glyphs or dynamically generated TikZ badges.

Terminal languages (Bash, Zsh, sh, PowerShell) display mac dots in the title
bar to reinforce their terminal identity. All other languages use clean
title bars with brand-colored icons.


Python
------

.. code-block:: python

   from dataclasses import dataclass
   from typing import Optional

   @dataclass
   class Document:
       """A styled document ready for PDF export."""
       title: str
       author: str
       version: Optional[str] = None

       def render(self) -> str:
           header = f"# {self.title} by {self.author}"
           if self.version:
               header += f" (v{self.version})"
           return header

   doc = Document("Doxtr Guide", "Theme Author", "1.0")
   print(doc.render())


Java
----

.. code-block:: java

   import java.util.List;
   import java.util.stream.Collectors;

   public class DocumentProcessor {
       private final List<String> chapters;

       public DocumentProcessor(List<String> chapters) {
           this.chapters = chapters;
       }

       public List<String> filterByKeyword(String keyword) {
           return chapters.stream()
               .filter(ch -> ch.contains(keyword))
               .collect(Collectors.toList());
       }
   }


Kotlin
------

.. code-block:: kotlin

   data class Theme(
       val name: String,
       val primaryColor: String,
       val isDark: Boolean = false
   )

   fun Theme.contrastColor(): String = when {
       isDark -> "#FFFFFF"
       else -> "#000000"
   }

   val doxtr = Theme("Doxtr", "#183060", isDark = true)
   println("${doxtr.name}: ${doxtr.contrastColor()}")


Rust
----

.. code-block:: rust

   use std::fmt;

   #[derive(Debug)]
   struct Color {
       r: u8,
       g: u8,
       b: u8,
   }

   impl Color {
       fn to_cmyk(&self) -> (f64, f64, f64, f64) {
           let r = self.r as f64 / 255.0;
           let g = self.g as f64 / 255.0;
           let b = self.b as f64 / 255.0;
           let k = 1.0 - r.max(g).max(b);
           if k >= 1.0 { return (0.0, 0.0, 0.0, 1.0); }
           let c = (1.0 - r - k) / (1.0 - k);
           let m = (1.0 - g - k) / (1.0 - k);
           let y = (1.0 - b - k) / (1.0 - k);
           (c, m, y, k)
       }
   }

   impl fmt::Display for Color {
       fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
           write!(f, "#{:02X}{:02X}{:02X}", self.r, self.g, self.b)
       }
   }


C
-

.. code-block:: c

   #include <stdio.h>
   #include <stdlib.h>
   #include <string.h>

   typedef struct {
       char name[64];
       int  priority;
   } Task;

   Task* create_task(const char* name, int priority) {
       Task* t = malloc(sizeof(Task));
       strncpy(t->name, name, sizeof(t->name) - 1);
       t->priority = priority;
       return t;
   }

   int main(void) {
       Task* task = create_task("Build PDF", 1);
       printf("Task: %s (priority %d)\n", task->name, task->priority);
       free(task);
       return 0;
   }


C++
---

.. code-block:: cpp

   #include <iostream>
   #include <vector>
   #include <algorithm>
   #include <string>

   template <typename T>
   class StyleRegistry {
   public:
       void add(const std::string& name, T value) {
           entries_.emplace_back(name, std::move(value));
       }

       auto find(const std::string& name) const {
           return std::find_if(entries_.begin(), entries_.end(),
               [&](const auto& e) { return e.first == name; });
       }

   private:
       std::vector<std::pair<std::string, T>> entries_;
   };


Go
--

.. code-block:: go

   package main

   import (
       "fmt"
       "strings"
   )

   type Theme struct {
       Name    string
       Primary string
       Dark    bool
   }

   func (t Theme) ContrastColor() string {
       if t.Dark {
           return "#FFFFFF"
       }
       return "#000000"
   }

   func main() {
       themes := []Theme{
           {"Doxtr", "#183060", true},
           {"Light", "#F8FAFF", false},
       }
       for _, t := range themes {
           fmt.Printf("%s → %s\n", t.Name, t.ContrastColor())
       }
       _ = strings.Join([]string{"a", "b"}, ", ")
   }


reStructuredText
----------------

.. code-block:: rst

   .. _my-reference-label:

   Chapter Title
   =============

   This is a paragraph with **bold** and *italic* text.

   .. note::

      This is an admonition inside RST source.

   .. code-block:: python

      print("Nested code block example")

   .. list-table:: Comparison
      :header-rows: 1

      * - Feature
        - Status
      * - PDF Output
        - ✓ Complete


Shell Script (sh)
-----------------

.. code-block:: sh

   #!/bin/sh
   set -eu

   PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
   BUILD_DIR="${PROJECT_DIR}/build"

   mkdir -p "${BUILD_DIR}"
   echo "Building in ${BUILD_DIR}..."

   find "${PROJECT_DIR}/src" -name "*.rst" -exec cp {} "${BUILD_DIR}" \;
   echo "Done. $(ls "${BUILD_DIR}" | wc -l) files copied."


Bash
----

.. code-block:: bash

   #!/bin/bash
   set -euo pipefail

   declare -A COLORS=(
       [primary]="#183060"
       [secondary]="#78D8F0"
       [warning]="#F0A860"
   )

   for name in "${!COLORS[@]}"; do
       printf "%-12s %s\n" "$name" "${COLORS[$name]}"
   done

   build_pdf() {
       local src="${1:?Source directory required}"
       sphinx-build -b latex "$src" build/latex/
       cd build/latex && latexmk -lualatex -quiet *.tex
   }

   build_pdf "${1:-source}"


Zsh
---

.. code-block:: zsh

   #!/usr/bin/env zsh
   setopt EXTENDED_GLOB NULL_GLOB

   typeset -A theme_colors
   theme_colors=(
       primary  "#183060"
       accent   "#78D8F0"
       danger   "#E05050"
   )

   for key val in ${(kv)theme_colors}; do
       print -P "%F{cyan}${key}%f → %F{white}${val}%f"
   done

   # Glob: all .tex_t files recursively, excluding build/
   templates=( **/*.tex_t~build/** )
   print "Found ${#templates} templates"


PowerShell
----------

.. code-block:: powershell

   #Requires -Version 7.0

   $ThemeConfig = @{
       Primary   = '#183060'
       Secondary = '#78D8F0'
       FontSize  = '11pt'
   }

   function Build-Documentation {
       [CmdletBinding()]
       param(
           [Parameter(Mandatory)]
           [string]$SourcePath,

           [ValidateSet('latex', 'html')]
           [string]$Builder = 'latex'
       )

       $outDir = Join-Path $SourcePath "build/$Builder"
       New-Item -ItemType Directory -Path $outDir -Force | Out-Null

       sphinx-build -b $Builder $SourcePath $outDir
       Write-Host "Build complete: $outDir" -ForegroundColor Green
   }

   Build-Documentation -SourcePath "./source"


Markdown
--------

.. code-block:: markdown

   # Doxtr PDF Theme

   > Professional LaTeX → PDF output for Sphinx projects.

   ## Features

   - **Three-tier merge** architecture
   - Per-language code styling with [dynamic icons](#icons)
   - WCAG-compliant contrast calculations

   ```python
   doc = Document("Example", author="Doxtr")
   doc.render()
   ```

   | Feature     | Status |
   |-------------|--------|
   | Code Blocks | ✓      |
   | Admonitions | ✓      |


HTML
----

.. code-block:: html

   <!DOCTYPE html>
   <html lang="en">
   <head>
       <meta charset="UTF-8">
       <title>Doxtr Theme Preview</title>
       <link rel="stylesheet" href="theme.css">
   </head>
   <body>
       <header class="dd-header">
           <h1>Doxtr PDF Theme</h1>
           <nav aria-label="Main navigation">
               <a href="#features">Features</a>
               <a href="#install">Install</a>
           </nav>
       </header>
       <main id="content">
           <section id="features">
               <h2>Features</h2>
               <p>Professional PDF output from Sphinx.</p>
           </section>
       </main>
   </body>
   </html>


CSS
---

.. code-block:: css

   :root {
       --dd-primary: #183060;
       --dd-secondary: #78D8F0;
       --dd-font-body: 'Spectral', serif;
       --dd-font-heading: 'Montserrat', sans-serif;
   }

   .dd-header {
       background: var(--dd-primary);
       color: white;
       padding: 1.5rem 2rem;
       display: flex;
       align-items: center;
       justify-content: space-between;
   }

   .dd-code-block {
       border-left: 3px solid var(--dd-secondary);
       background: #F8FAFF;
       padding: 1em;
       font-family: 'FiraCode NF', monospace;
       font-size: 0.9em;
       overflow-x: auto;
   }


JavaScript
----------

.. code-block:: javascript

   class ThemeEngine {
       #config;
       #resolvedColors = new Map();

       constructor(config) {
           this.#config = structuredClone(config);
       }

       resolveColor(expr) {
           if (this.#resolvedColors.has(expr)) {
               return this.#resolvedColors.get(expr);
           }
           const resolved = expr.startsWith('dd:')
               ? this.#evaluateExpression(expr)
               : expr;
           this.#resolvedColors.set(expr, resolved);
           return resolved;
       }

       #evaluateExpression(expr) {
           const [, ref, ...ops] = expr.split(':');
           let color = this.#config.palette[ref] ?? '#000000';
           // Apply operations (lighten, darken, contrast)
           return color;
       }
   }

   const engine = new ThemeEngine({ palette: { primary: '#183060' } });
   console.log(engine.resolveColor('dd:primary'));


TypeScript
----------

.. code-block:: typescript

   interface SemanticPalette {
       primary: string;
       secondary: string;
       info: string;
       success: string;
       warning: string;
       danger: string;
   }

   type ColorOperation = 'lighten' | 'darken' | 'contrast';

   function resolveDD(
       expr: string,
       palette: SemanticPalette
   ): string {
       const parts = expr.replace('dd:', '').split(':');
       const baseKey = parts[0] as keyof SemanticPalette;
       const baseColor = palette[baseKey];

       if (parts.length === 1) return baseColor;

       const operation = parts[1] as ColorOperation;
       const amount = parseInt(parts[2] ?? '50', 10);
       return applyOperation(baseColor, operation, amount);
   }


Plain Text
----------

.. code-block:: text

   Doxtr PDF Theme Core — Architecture Overview
   ================================================

   Three-Tier Merge:
     1. Core Defaults  (core_config.py)
     2. Theme Overrides (doxtr_theme_defaults)
     3. User Config     (conf.py variables)

   Template Resolution:
     Custom Path → User Project → Theme → Core → Fallback

   Color Pipeline:
     Hex Input → CMYK Conversion → LaTeX Color Definition


JSON
----

.. code-block:: json

   {
       "doxtr_semantic_palette": {
           "primary": "#183060",
           "secondary": "#78D8F0",
           "info": "#60D8F0",
           "success": "#66D98E",
           "warning": "#F0A860",
           "danger": "#E05050"
       },
       "code_languages": [
           { "name": "python", "icon": "faIcon", "mac_dots": false },
           { "name": "bash", "icon": "tikz_dynamic", "mac_dots": true }
       ]
   }


YAML
----

.. code-block:: yaml

   # Doxtr theme configuration
   doxtr:
     semantic_palette:
       primary: "#183060"
       secondary: "#78D8F0"
       info: "#60D8F0"

     code:
       generic:
         border_width: "0.8pt"
         show_mac_dots: false
         content_font: "FiraCode Nerd Font"

       bash:
         show_mac_dots: true
         title_background_color: "#2E3436"
         title_font_color: "#8AE234"


SQL
---

.. code-block:: sql

   CREATE TABLE themes (
       id          SERIAL PRIMARY KEY,
       name        VARCHAR(64) NOT NULL UNIQUE,
       primary_hex CHAR(7) NOT NULL DEFAULT '#183060',
       is_dark     BOOLEAN NOT NULL DEFAULT FALSE,
       created_at  TIMESTAMP WITH TIME ZONE DEFAULT NOW()
   );

   SELECT t.name,
          t.primary_hex,
          COUNT(c.id) AS color_count
   FROM   themes t
   LEFT JOIN colors c ON c.theme_id = t.id
   WHERE  t.is_dark = TRUE
   GROUP BY t.id, t.name, t.primary_hex
   ORDER BY color_count DESC
   LIMIT 10;


XML
---

.. code-block:: xml

   <?xml version="1.0" encoding="UTF-8"?>
   <theme name="doxtr-core" version="0.1.6">
       <palette>
           <color role="primary">#183060</color>
           <color role="secondary">#78D8F0</color>
           <color role="danger">#E05050</color>
       </palette>
       <fonts>
           <font type="main">Spectral</font>
           <font type="sans">Montserrat</font>
           <font type="mono">FiraCode Nerd Font</font>
       </fonts>
   </theme>


LaTeX
-----

.. code-block:: latex

   \documentclass[a4paper,11pt]{scrbook}
   \usepackage{fontspec}
   \usepackage{tcolorbox}
   \tcbuselibrary{skins, breakable}

   \setmainfont{Spectral}
   \setsansfont{Montserrat}
   \setmonofont{FiraCode Nerd Font}

   \definecolor{ddprimary}{HTML}{183060}
   \definecolor{ddsecondary}{HTML}{78D8F0}

   \newtcolorbox{ddcodebox}[1][]{%
       enhanced, breakable,
       colback=ddprimary!5, colframe=ddsecondary,
       fonttitle=\sffamily\bfseries,
       title={Code}, #1
   }

   \begin{document}
   \begin{ddcodebox}[title={Example}]
       Hello from \LaTeX!
   \end{ddcodebox}
   \end{document}


Dockerfile
----------

.. code-block:: dockerfile

   FROM python:3.12-slim AS builder

   WORKDIR /app
   COPY pyproject.toml .
   RUN pip install --no-cache-dir build \
       && python -m build --wheel

   FROM authsec/doxtr:0.0.10
   COPY --from=builder /app/dist/*.whl /tmp/
   RUN pip install /tmp/*.whl && rm /tmp/*.whl

   WORKDIR /docs
   COPY source/ source/
   COPY conf.py .

   ENTRYPOINT ["sphinx-build", "-b", "latex", "source/", "build/"]


TOML
----

.. code-block:: toml

   [build-system]
   requires = ["setuptools>=68.0", "wheel"]
   build-backend = "setuptools.build_meta"

   [project]
   name = "doxtr-pdf-theme-core"
   version = "0.1.6"
   description = "Professional LaTeX PDF theme for Sphinx"
   requires-python = ">=3.10"
   license = {text = "MIT"}

   [project.optional-dependencies]
   dev = ["sphinx>=7.0", "sphinx-needs>=2.0"]

   [tool.setuptools.packages.find]
   include = ["doxtr_pdf_theme_core*"]


Ruby
----

.. code-block:: ruby

   # frozen_string_literal: true

   module Doxtr
     class Theme
       attr_reader :name, :palette

       def initialize(name, palette = {})
         @name = name
         @palette = default_palette.merge(palette)
       end

       def contrast_color(hex)
         r, g, b = hex.scan(/\w{2}/).map { |c| c.to_i(16) / 255.0 }
         luminance = 0.2126 * r + 0.7152 * g + 0.0722 * b
         luminance > 0.5 ? '#000000' : '#FFFFFF'
       end

       private

       def default_palette
         { primary: '#183060', secondary: '#78D8F0' }
       end
     end
   end


PHP
---

.. code-block:: php

   <?php

   declare(strict_types=1);

   namespace Doxtr\Theme;

   class ColorConverter
   {
       public function hexToCmyk(string $hex): array
       {
           $hex = ltrim($hex, '#');
           $r = hexdec(substr($hex, 0, 2)) / 255;
           $g = hexdec(substr($hex, 2, 2)) / 255;
           $b = hexdec(substr($hex, 4, 2)) / 255;

           $k = 1 - max($r, $g, $b);
           if ($k >= 1.0) {
               return [0.0, 0.0, 0.0, 1.0];
           }

           return [
               'c' => (1 - $r - $k) / (1 - $k),
               'm' => (1 - $g - $k) / (1 - $k),
               'y' => (1 - $b - $k) / (1 - $k),
               'k' => $k,
           ];
       }
   }


Makefile
--------

.. code-block:: make

   .PHONY: all clean pdf install

   SPHINX_OPTS  ?= -W --keep-going
   SOURCE_DIR   := source
   BUILD_DIR    := build
   LATEX_DIR    := $(BUILD_DIR)/latex

   all: pdf

   pdf: $(LATEX_DIR)/doxtr.pdf

   $(LATEX_DIR)/doxtr.pdf: $(shell find $(SOURCE_DIR) -name '*.rst')
   	sphinx-build -b latex $(SPHINX_OPTS) $(SOURCE_DIR) $(LATEX_DIR)
   	cd $(LATEX_DIR) && latexmk -lualatex -quiet *.tex

   install:
   	pip install -e .

   clean:
   	rm -rf $(BUILD_DIR)
