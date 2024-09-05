# Copyright 2024 The LUCI Authors.
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

# Based on:
# https://source.chromium.org/chromium/infra/infra_superproject/+/main:infra/go/src/go.chromium.org/luci/analysis/frontend/ui/scripts/gen_proto.sh

cd "$(dirname "$0")"
cd ..
rm -rf ./client/src/proto
mkdir ./client/src/proto

# Use ts-proto instead of the official grpc-web because it is RPC framework
# agnostic. This is crucial because we use a non-standard protocol (pRPC) for
# client-server communication.
protoc \
  --plugin=./client/node_modules/.bin/protoc-gen-ts_proto \
  \
  `# All the base directory to resolve the proto file dependencies from must be
   # listed here. Otherwise, protoc may not able to resolve the dependencies
   # listed in a proto file.` \
  -I=./ \
  \
  --ts_proto_out=./client/src/proto \
  \
  `# Add '.pb' so it can be ignored by presubmit upload checks.` \
  --ts_proto_opt=fileSuffix=.pb \
  \
  `# Do not use ExactTypes because
   #  * It hinders productivity.
   #    * When used with useReadonlyTypes, it prevents the use of array literal
   #      unless some form of type casting is usesd. Type casting is verbose and
   #      breaks the type guarantee that ExactType is trying to enforce.
   #    * It uses complex recursive types that slow down the compiler.
   #  * It delivers very little benefit.
   #    * TypeScript already prevents declaring unknown properties in an object
   #      literal.
   #  * Fundamentally, we don't want this behavior.
   #    * When .fromPartial or .create is fed with a non-literal object, we want
   #      the extra properties to be silently discarded. Otherwise, adding a new
   #      field to a proto message will become a breaking change if the proto
   #      message is used to construct another proto message that is a subtype
   #      of this message.` \
  --ts_proto_opt=useExactTypes=false \
  \
  `# Do not use remove enum prefix because it will generate invalid enum variant
   # identifiers when the identifier begins with a digit after the prefix is
   # removed.` \
  --ts_proto_opt=removeEnumPrefix=false \
  \
  --ts_proto_opt=forceLong=string,esModuleInterop=true \
  --ts_proto_opt=unrecognizedEnum=false \
  --ts_proto_opt=useDate=string,useReadonlyTypes=true \
  \
  ./apipb/device.proto \