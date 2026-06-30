from app.agent.poultry_agent import PoultryAgent


def test_mutating_commands_request_confirmation():
    assert PoultryAgent.should_request_confirmation('add 5 kg feed to inventory') is True
    assert PoultryAgent.should_request_confirmation('remove 2 bags of medicine') is True
    assert PoultryAgent.should_request_confirmation('please delete this transaction') is True


def test_read_only_commands_do_not_request_confirmation():
    assert PoultryAgent.should_request_confirmation('show me today\'s feed expense') is False
    assert PoultryAgent.should_request_confirmation('what is the inventory status') is False
