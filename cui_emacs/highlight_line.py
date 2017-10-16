# Copyright (c) 2017 Christoph Landgraf. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import cui_emacs

highlight_line = cui_emacs.declare_function('cui/highlight-line')
unhighlight_line = cui_emacs.declare_function('cui/unhighlight-line')
remove_overlay = cui_emacs.declare_function('cui/remove-overlay')
remove_overlays = cui_emacs.declare_function('cui/remove-overlays')
