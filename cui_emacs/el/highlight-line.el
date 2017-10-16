;; Copyright (c) 2017 Christoph Landgraf. All rights reserved.
;; Use of this source code is governed by a BSD-style license that can be
;; found in the LICENSE file.

;; TODO tooltip
;; TODO window prop optional

(defface cui/highlight
  '((t :background "#444400"))
  "Debugger highlighting current code position")

(defcustom cui/highlight-face 'cui/highlight
  "Face with which to highlight the current line in Hl-Line mode."
  :type 'face)

(defvar cui/overlays (make-hash-table :test #'equal))

(defvar cui/overlay-windows (make-hash-table :test #'equal))

(defun cui/highlight-line (overlay-id file-name line-number)
  (let ((the-point (cui/display-line file-name
                                     line-number
                                     (gethash overlay-id cui/overlay-windows))))
    (if the-point
        (save-excursion
          (puthash overlay-id (selected-window) cui/overlay-windows)
          (goto-char the-point)
          (cui/show-overlay overlay-id)))))

(defun cui/show-overlay (overlay-id)
  (let ((overlay (or (gethash overlay-id cui/overlays)
                     (puthash overlay-id
                              (cui/make-overlay overlay-id)
                              cui/overlays))))
    ;(overlay-put overlay 'window (selected-window))
    (move-overlay overlay (line-beginning-position) (line-beginning-position 2) (current-buffer))))

(defun cui/unhighlight-line (overlay-id)
  (let ((overlay (gethash overlay-id cui/overlays)))
    (if overlay
        (delete-overlay (gethash overlay-id cui/overlays)))))

(defun cui/make-overlay (overlay-id)
  (let ((overlay (make-overlay (point) (point))))
    (overlay-put overlay 'help-echo overlay-id)
    (overlay-put overlay 'priority -40)
    (overlay-put overlay 'face cui/highlight-face)
    overlay))

(defun cui/remove-overlay (overlay-id)
  (cui/unhighlight-line overlay-id)
  (remhash overlay-id cui/overlay-windows)
  (remhash overlay-id cui/overlays))

(defun cui/remove-overlays ()
  (maphash (lambda (k v) (message k) (cui/remove-overlay k))
           cui/overlays))

(defun cui/display-line (file-name line-number &optional window)
  (let ((buffer (find-file-noselect file-name)))
    (if (null buffer)
        (message "Cannot access file.")
      (select-window (if (and window (window-live-p window))
                         (progn
                           (switch-to-buffer buffer)
                           window)
                       (display-buffer buffer)))
      (save-excursion
        (goto-char 0)
        (forward-line (- line-number 1))
        (recenter)
        (point)))))


(cui/highlight-line "test/overlay"
                    "c:/src/cs/applications/cs.all/trunk/package_sources/cs.web/cs/web/components/base/js/src/formcontrols/TextInput.jsx"
                    132)
(cui/unhighlight-line "test/overlay")
(cui/remove-overlay "test/overlay")
(cui/remove-overlays)
