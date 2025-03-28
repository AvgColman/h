from unittest import mock
from unittest.mock import sentinel

import pytest

from h import models
from h.services.user_rename import UserRenameError, UserRenameService, service_factory


class TestUserRenameService:
    def test_check_returns_true_when_new_username_does_not_exist(self, service, user):
        assert service.check(user, "panda") is True

    def test_check_raises_when_new_userid_is_already_taken(
        self, service, user, db_session, factories
    ):
        factories.User(username="panda")
        db_session.flush()

        with pytest.raises(UserRenameError) as err:
            service.check(user, "panda")
        assert str(err.value) == 'Another user already has the username "panda"'

    @mock.patch("h.models.user.User.get_by_username")
    def test_check_returns_True_if_new_username_equivalent_to_old(
        self, get_by_username, service, user
    ):
        """
        check() should return True if the new username is equivalent to the old.

        It's possible to have two different usernames, for example "bob.smith"
        and "Bob.Smith", that are "equivalent" in that they both reduce to the
        same normalised username "bobsmith". While we can't allow two
        different users to have the usernames "bob.smith" and "Bob.Smith", we
        _should_ allow renaming a single "bob.smith" user to "Bob.Smith".

        get_by_username() returns a User whose username is the same as or
        equivalent to the given username. If the returned User is the same user
        who we're trying to rename, we should allow the rename operation to go
        ahead.

        """
        get_by_username.return_value = user

        assert service.check(user, "panda") is True

    def test_rename(self, service, check, user, factories, db_session):
        ids = [factories.AuthTicket(user=user).id for _ in range(3)]
        token = factories.DeveloperToken(user=user)
        requested_by = factories.User()
        old_userid = user.userid

        service.rename(user, "panda", requested_by, "tag")

        check.assert_called_once_with(service, user, "panda")
        assert db_session.get(models.User, user.id).username == "panda"
        assert not (
            db_session.query(models.AuthTicket)
            .filter(models.AuthTicket.id.in_(ids))
            .count()
        )
        assert (
            db_session.query(models.Token)
            .filter(models.Token.id == token.id)
            .one()
            .user
            == user
        )
        user_rename = db_session.query(models.UserRename).first()
        assert user_rename.old_userid == old_userid
        assert user_rename.new_userid == user.userid

    @pytest.mark.usefixtures("annotations")
    def test_rename_changes_the_users_annotations_userid(
        self, service, user, db_session, factories
    ):
        service.rename(user, "panda", factories.User(), "tag")

        userids = [ann.userid for ann in db_session.query(models.Annotation)]
        assert {user.userid} == set(userids)

    def test_rename_reindexes_the_users_annotations(
        self, service, user, tasks, factories
    ):
        original_userid = user.userid

        service.rename(user, "panda", factories.User(), "tag")

        tasks.job_queue.add_annotations_from_user.delay.assert_called_once_with(
            "sync_annotation",
            original_userid,
            tag="RenameUserService.rename",
            schedule_in=30,
        )

    @pytest.fixture
    def service(self, pyramid_request):
        return UserRenameService(db=pyramid_request.db)

    @pytest.fixture
    def check(self, patch):
        return patch("h.services.user_rename.UserRenameService.check")

    @pytest.fixture
    def user(self, factories, db_session):
        user = factories.User(username="giraffe")
        db_session.flush()
        return user

    @pytest.fixture
    def annotations(self, user, factories, db_session):
        anns = []
        for _ in range(8):
            anns.append(factories.Annotation(userid=user.userid))  # noqa: PERF401
        db_session.add_all(anns)
        db_session.flush()

        return anns

    @pytest.fixture(autouse=True)
    def tasks(self, patch):
        return patch("h.services.user_rename.tasks")


class TestServiceFactory:
    def test_it(self, pyramid_request, UserRenameService):
        svc = service_factory(sentinel.context, pyramid_request)

        UserRenameService.assert_called_once_with(db=pyramid_request.db)
        assert svc == UserRenameService.return_value

    @pytest.fixture
    def UserRenameService(self, patch):
        return patch("h.services.user_rename.UserRenameService")
