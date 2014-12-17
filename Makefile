# Copyright (C) 2014 Red Hat, Inc.
#
# This file is part of csmock.
#
# csmock is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# any later version.
#
# csmock is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with csmock.  If not, see <http://www.gnu.org/licenses/>.

CMAKE ?= cmake
CTEST ?= ctest

.PHONY: all check clean distclean distcheck install

all:
	mkdir -p csmock_build
	cd csmock_build && $(CMAKE) ..
	$(MAKE) -C csmock_build

check: all
	cd csmock_build && $(CTEST) --output-on-failure

clean:
	if test -e csmock_build/Makefile; then $(MAKE) clean -C csmock_build; fi

distclean:
	rm -rf csmock_build

distcheck: distclean
	$(MAKE) check

install: all
	$(MAKE) -C csmock_build install
