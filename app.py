import routeros_api
import datetime
import pytz

# MikroTik Router Configuration
ROUTER_IP = 'server3.remotemikrotik.com'
USERNAME = 'admin'
PASSWORD = 'A35QOGURSS'
PORT = 7026
TIMEZONE = pytz.timezone('Africa/Nairobi')

def log_event(message):
    timestamp = datetime.datetime.now(TIMEZONE).strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {message}"
    print(log_entry)

def get_router_connection():
    try:
        api_pool = routeros_api.RouterOsApiPool(
            ROUTER_IP, username=USERNAME, password=PASSWORD, port=PORT, plaintext_login=True
        )
        router = api_pool.get_api()
        return api_pool, router
    except routeros_api.exceptions.RouterOsApiConnectionError as e:
        log_event(f"Connection Error: {str(e)}")
        return None, None

def parse_time_string(time_str):
    formats = ["%Y-%m-%d %H:%M:%S", "%H:%M:%S"]
    for fmt in formats:
        try:
            return datetime.datetime.strptime(time_str, fmt)
        except ValueError:
            continue
    raise ValueError(f"time data '{time_str}' does not match any expected format")

def remove_expired_users():
    api_pool, router = get_router_connection()
    if router is None:
        return

    try:
        current_time = datetime.datetime.now(TIMEZONE)
        current_time_str = current_time.strftime('%Y-%m-%d %H:%M:%S')
        log_event(f"Current time: {current_time_str}")

        hotspot_users = router.get_resource('/ip/hotspot/user')
        active_users = router.get_resource('/ip/hotspot/active')
        users = hotspot_users.get()

        for user in users:
            comment = user.get('comment', '')
            if 'expires:' in comment:
                exp_time_str = comment.split('expires:')[1].strip()
                try:
                    exp_time = parse_time_string(exp_time_str)
                    if exp_time.time() == exp_time:
                        exp_time = exp_time.replace(
                            year=current_time.year,
                            month=current_time.month,
                            day=current_time.day
                        )
                    exp_time = TIMEZONE.localize(exp_time)
                    log_event(f"User: {user['name']} expires at: {exp_time_str}")

                    if current_time > exp_time:
                        log_event(f"Removing expired user: {user['name']}")
                        if 'id' in user:
                            hotspot_users.remove(id=user['id'])
                            # Log out user from active sessions
                            active_sessions = active_users.get(username=user['name'])
                            for session in active_sessions:
                                active_users.remove(id=session['.id'])
                        else:
                            log_event(f"Error: User ID not found for {user['name']}")
                            log_event(f"User object: {user}")
                except ValueError as e:
                    log_event(f"Error parsing time: {exp_time_str}, Error: {str(e)}")
    except Exception as e:
        log_event(f"Error: {str(e)}")
    finally:
        api_pool.disconnect()

if __name__ == '__main__':
    remove_expired_users()
