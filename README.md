# Twitter List Syncer
A python tool to sync Twitter lists between two accounts.

## Usage
### Get Twitter API keys
You need to create an app on the [Twitter developer page](https://developer.twitter.com/en/apps) for each of the two accounts.
To do that, both accounts have to be Twitter developer accounts.

After creating the two apps, you can generate access tokens and secrets for both (see [here](https://developer.twitter.com/en/docs/basics/authentication/oauth-1-0a)).
Please give them read & write permissions, direct message permissions are only required if you want to send a summary dm between the two accounts
after syncing has finished.

You can paste the consumer keys & secrets and the access token keys & secrets into a file called `env` (see [env.sample](env.sample) for the format).

### Run in terminal
Install the required [python-twitter](https://github.com/bear/python-twitter) package using `$ pip3 install -r requirements.txt`.

You can now load the environment variables using `$ source env` and then run the script with `$ python3 main.py`.
If you add the `-v` flag, output will be verbose. The `--dm` flag sends a summary dm from the first account to the second after syncing.

### Exclude lists from syncing
If you want to exclude a list, just add the word "exclude" in the description of that list.

## Automation

I've deployed this script to an AWS Lambda function which runs once every day using a CloudWatch scheduled rule.
To achieve that, I used [this](https://github.com/appleboy/lambda-action) GitHub action.

I uploaded the environment variables using the [aws-cli](https://github.com/aws/aws-cli) with the following command:
```
$ aws lambda update-function-configuration \
  --function-name FUNCTION_NAME_HERE \
  --environment Variables="{`cat env_aws | xargs | sed 's/ /,/g'`}"
```
The format is similar to the `env` file, see [env_aws.sample](env_aws.sample).