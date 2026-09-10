error_messages = {
    "db_insert_failed": "The data could not be saved. Please try again in a few minutes.",
    "db_select_failed": "Temporary database issues. Please refresh the page.",
    "db_update_failed": "The site status could not be updated. Please try again.",
    "db_delete_failed": "The site could not be deleted. Please try again.",
    "site_not_found": "That page was not found.",
    "total_links_reached": "The limit of 50 sites has been reached.",
    "total_active_links_reached": "No more than 5 websites can be active at the same time.",
    "invalid_url": "Invalid website address.",
    "empty_url": "Please enter a website address.",
    "url_too_long": "The website address is too long.",
    "invalid_scheme": "Invalid website scheme.",
}

def get_user_message(error_code):
    return error_messages.get(error_code, "An unknown error has occurred. Please try again later.")