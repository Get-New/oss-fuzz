# Copyright 2019 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
################################################################################

FROM gcr.io/oss-fuzz-base/base-builder
MAINTAINER skau@google.com

RUN apt-get update && apt-get install -y autoconf zlibc liblcms2-dev libfreetype6-dev libpng-dev libtiff-dev
RUN git clone --branch branch-2.2 --single-branch --depth 1 https://github.com/apple/cups.git cups
RUN git clone --single-branch --depth 1 git://git.ghostscript.com/ghostpdl.git ghostpdl

RUN mkdir ghostpdl/fuzz
COPY gstoraster_fuzzer.cc ghostpdl/fuzz

COPY build.sh $SRC/
