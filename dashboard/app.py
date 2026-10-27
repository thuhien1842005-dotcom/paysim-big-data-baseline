"""Chỉ bật MỘT lựa chọn. Giữ nguyên các dòng marker và chú thích."""
from dashboard_core import render

# BEFORE Start — 9: dashboard gốc
# view = None
# BEFORE END — 9

# AFTER Start — 9A: Operations / 5 thay đổi giao diện
# import view_operations as view
# AFTER END — 9A

# AFTER Start — 9B: Report / 5 thay đổi giao diện
import view_report as view
# AFTER END — 9B

# AFTER Start — 9C: Studio / 5 thay đổi giao diện
# import view_studio as view
# AFTER END — 9C

# Dòng này giữ nguyên cho cả BEFORE và ba AFTER.
# render(view)
