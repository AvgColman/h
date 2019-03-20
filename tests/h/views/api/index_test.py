# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import pytest
import mock

from pyramid.config import Configurator

from h.views.api import index as views


class TestIndex(object):
    def test_it_returns_links(self, pyramid_request):
        result = views.index(None, pyramid_request)

        assert "links" in result

    def test_it_instantiates_a_templater(self, pyramid_request, AngularRouteTemplater):
        views.index(None, pyramid_request)

        AngularRouteTemplater.assert_called_once_with(
            pyramid_request.route_url,
            params=["id", "pubid", "user", "userid", "username"],
        )

    def test_it_returns_links_for_the_right_version(
        self, pyramid_request, AngularRouteTemplater, link_helpers
    ):
        views.index(None, pyramid_request)

        link_helpers.format_nested_links.assert_called_once_with(
            pyramid_request.registry.api_links["v1"],
            "v1",
            AngularRouteTemplater.return_value,
        )

    @pytest.fixture
    def pyramid_request(self, pyramid_config, pyramid_request):
        # Scan `h.views.api_annotations` for API link metadata specified in @api_config
        # declarations.
        config = Configurator()
        config.scan("h.views.api.annotations")
        # Any route referenced in `h.views.api.annotations` needs to be added here
        pyramid_config.add_route("api.search", "/dummy/search")
        pyramid_config.add_route("api.annotations", "/dummy/annotations")
        pyramid_config.add_route("api.annotation", "/dummy/annotations/:id")
        pyramid_request.registry.api_links = config.registry.api_links

        pyramid_request.route_url = mock.Mock()
        return pyramid_request

    @pytest.fixture
    def link_helpers(self, patch):
        return patch("h.views.api.index.link_helpers")

    @pytest.fixture
    def AngularRouteTemplater(self, patch):
        return patch("h.views.api.index.AngularRouteTemplater")
