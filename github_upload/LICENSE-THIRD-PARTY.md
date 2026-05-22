# Third-Party Licenses

Compatible Bodies Tooltip bundles or depends on the following third-party software. Each is used under the terms of its respective license.

## LSLib (Divine.exe)

**Project:** LSLib by Norbyte
**Source:** https://github.com/Norbyte/lslib
**License:** MIT
**Used as:** The sidecar bundles `divine.exe` (the command-line interface to LSLib) for unpacking BG3 `.pak` files during cache regeneration.

```
MIT License

Copyright (c) Norbyte

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

For the canonical license text, see the LSLib repository's `LICENSE` file.

## BG3 Script Extender (BG3SE)

**Project:** BG3 Script Extender by Norbyte
**Source:** https://github.com/Norbyte/bg3se
**License:** MIT
**Used as:** Runtime dependency. The mod's `BootstrapClient.lua` script is loaded by BG3SE; we do not bundle or redistribute BG3SE itself — end users must install it separately.

## lxml (Python)

**Project:** lxml
**Source:** https://lxml.de/
**License:** BSD-3-Clause
**Used as:** Python sidecar dependency for XML parsing. Not bundled; installed by the end user via `pip install lxml` per the install instructions.

## Notes

Compatible Bodies Tooltip itself (the `.pak` contents, the sidecar Python scripts, and accompanying documentation) is licensed under MIT — see `LICENSE`. The bundling and use of LSLib's `divine.exe` is permitted by LSLib's MIT license, with attribution preserved here.
