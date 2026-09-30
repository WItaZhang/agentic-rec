from src.batch_scheduler import may_recover_upload


def test_only_precreation_connection_errors_receive_bounded_upload_recovery():
    connection = {'stage': 'file_upload', 'type': 'APIConnectionError', 'http_status': None}
    assert may_recover_upload(connection, 0, 2)
    assert not may_recover_upload(connection, 2, 2)
    assert not may_recover_upload(connection, 0, 0)
    assert not may_recover_upload({**connection, 'stage': 'batch_create'}, 0, 2)
    assert not may_recover_upload({**connection, 'type': 'BadRequestError', 'http_status': 400}, 0, 2)
