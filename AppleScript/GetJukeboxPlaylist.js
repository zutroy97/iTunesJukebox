// AppleKey-Shift-P to bring up command palette
// JAX: Run Script


// Dumps the Jukebox Playlist as a dictonary of PersistentId as the key
// and an object containing info about the tracks in JSON format.
//var itunes = Application('iTunes');
var itunes = Application('Music');
itunes.includeStandardAdditions = true;

function run(argv) {
    let tracks = GetPlaylistTracksAsDictionary("Jukebox");
	return JSON.stringify(tracks);
}

function GetPlaylistTracksAsDictionary(playlistName)
{
	let results = {};
    var jukeboxPlaylist = itunes.playlists[playlistName];
	for(var i = 0; i < jukeboxPlaylist.tracks.length; i++){
		var track = jukeboxPlaylist.tracks[i];
		var x = new Object();
        x.Name = track.name();
        x.Index = i;
        x.Artist = track.artist();
        x.Album = track.album();
        x.PlayedCount = track.playedCount();
        x.ReleaseYear = track.year();
		results[track.persistentID().toUpperCase()] = x;
	}
	return results;
}
