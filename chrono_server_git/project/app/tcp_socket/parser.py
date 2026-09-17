from datetime import datetime, timedelta, timezone

def timestamp_from_string(string):
    """

    :param string: format - YYMMDDHHMMSSMS
    :return:
    """
    full_date = '20' + string

    dt_object = datetime.strptime(full_date, '%Y%m%d%H%M%S%f')
    time = dt_object.replace(tzinfo=timezone.utc).timestamp()
    return time


def date_time_from_short_string(string):
    """

    :param string: format - MMDDHHMM
    :return:
    """
    full_date = '2026' + string

    dt_object = datetime.strptime(full_date, '%Y%m%d%H%M').replace(tzinfo=timezone.utc)
    return dt_object


def timestamp_from_short_string(string):
    """

    :param string: format - MMDDHHMM
    :return:
    """
    full_date = '2026' + string

    dt_object = datetime.strptime(full_date, '%Y%m%d%H%M')
    time = dt_object.replace(tzinfo=timezone.utc).timestamp()
    return time


def check_data_type(data):
        """
        check data type received from device
        results:
        1 - normal
        2 - immediate
        3 - keyed
        ping:
        4 - ping
        5 - ping answer with time
        info:
        6 - device info
        error:
        9 - error

        :param data:
        :return: int
        """
        if data[0] == 'TO':
            if data[10] == 'P':
                return 1
            elif data[10] == 'I':
                return 2
            elif data[10] == 'K':
                return 3
            else:
                return 9
        elif data[0] == 'PING':
            return 4
        elif data[0] == 'ACK' and data[1] == 'PING':
            return 5
        elif data[0] == 'MK':
            return 6
        else:
            return 9