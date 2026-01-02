from content_filter import ContentFilter

def debug_censorship(text):
    cf = ContentFilter()
    has_violation, details = cf.check_content(text)
    print(f"Text: {text}")
    print(f"Violation: {has_violation}")
    print(f"Details: {details}")
    summary = cf.get_violation_summary(details)
    print(f"Summary: {summary}")

if __name__ == "__main__":
    debug_censorship("1girl, (best quality:1.2), (side view:1.3)")
