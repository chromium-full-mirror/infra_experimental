const { WebClient } = require('@slack/web-api');
const fetch = require('node-fetch');

// Create a new instance of the WebClient class with the token read from your environment variable
const web = new WebClient(process.env.SLACK_TOKEN);

// Update the topic for the channel_id. This requires the numeric id and not
// a string like #general.
//
// The function also does a best-effort dedupe based on string comparison.
// It is easy to trip this up though because slack will escape the topic
// string. Unless the calling code reads back the set topic and handles
// appropriately, it will be easy to accidentally defeat the update logic.
async function updateTopic(channel_id, new_topic) {
   const info = await web.conversations.info({
     channel: channel_id,
   });
   if (info && info.ok && info.channel.topic.value !== new_topic) {
     await web.conversations.setTopic({
       channel: channel_id, 
       topic: new_topic
     });
   }
}

exports.helloGET = (req, res) => {
  // The current date
  const currentTime = new Date().toTimeString();
  (async () => {
   // Use the `chat.postMessage` method to send a message from this app
   await web.chat.postMessage({
     channel: '#bots',
     text: `HELLO WHIRLED! The current time is ${currentTime}`,
     });
   })();
  res.send("Hello has been whirled.");
};

exports.updateSheriff = (req, res) => {
  (async () => {
     const response = await fetch("https://rota-ng.appspot.com/legacy/sheriff.json");
     const sheriff_data = await response.json();
     const usernames = [];
     for (let email of sheriff_data.emails) {
      usernames.push(email.split("@")[0])
     }

     // Careful with the string format. The dedup logic in updateTopic is based on
     // string equality and slack modifies/escapes the topic string.
     //
     // TODO(ajwong): store the data in the realtimedb or something for dedupe.
     const newTopic = `sheriffs: ${usernames.join(", ")}, <https://sheriff-o-matic.appspot.com/chromium> <https://chromium.googlesource.com/chromium/src/+/HEAD/docs/sheriff.md>`;

     //const botsChannelId = 'CGHGPLSF5'; // #bots
     const sheriffsChannelId = 'CGJ5WKRUH'; // #sheriffing
     await updateTopic(sheriffsChannelId, newTopic);
     })();
  res.send("#sheriffing updated.");
};
