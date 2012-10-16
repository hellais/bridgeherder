# Getting started

You will need to have installed virtualenv and git.

You can do so on debian with:

  apt-get install virtualenv git

Clone the repo with:

  git clone https://example.com
  cd bridgeherder

Then create a virtual env for it with:

  virtualenv -p python2.7 ENV
  pip install -r requirements.txt
  ./bin/bridgeherder
