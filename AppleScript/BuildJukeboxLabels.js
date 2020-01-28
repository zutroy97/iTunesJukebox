// AppleKey-Shift-P to bring up command palette
// JAX: Run Script

// Takes the Jukebox playlist and calles a webpage to generate
// labels to fit the jukebox

var app = Application.currentApplication();
app.includeStandardAdditions = true;

var itunes = Application('iTunes');
itunes.includeStandardAdditions = true;

var safari = Application("Safari");
safari.includeStandardAdditions = true;;
//safari.activate();

function run(argv) {
    //let tracks = GetPlaylistTracksAsDictionary("iTunes Artwork Screen Saver");
    let tracks = GetPlaylistTracksAsDictionary("Jukebox");
    var i = 0;
    var isMoreLabels = false;
    do{
        isMoreLabels = CreatePageOfLabels(i++, tracks);
    }while(isMoreLabels && (i < 10));

    return 'finished';
}

function CreateSafariJukeboxTab()
{
    var tab = safari.Tab();
    tab.url = "https://www.mikesarcade.com/arcade/titlestrips.html";
    if (safari.windows.length == 0)
    {
        console.log("No Safari windows");
        safari.windows.push(new safari.window());
    }
    safari.windows[0].tabs.push(tab);
    safari.windows[0].currentTab=tab;
    var readyState = '';
    var i = 0;
    do{
        i++;
        readyState = safari.doJavaScript('document.readyState', {in: tab});
        app.doShellScript('sleep 1;'); // Give the webpage a moment for JS to initialize.
    }while(readyState != 'complete' && i < 5);
    return tab;
}
function GetPlaylistTracksAsDictionary(playlistName)
{
	let results = [];
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
        x.PersistentId = track.persistentID();
		results[i] = x;
	}
	return results;
}

function SetField(tab, tagInfo)
{
    var field = 'titlea[' + tagInfo.TagGeneratorRow + ']';
    var value = tagInfo.TrackA.Track.Name;
    setFieldByName(tab, field, value);
    field = 'artista[' + tagInfo.TagGeneratorRow + ']';
    value = tagInfo.TrackA.Track.Artist;
    setFieldByName(tab, field, value);

    if (tagInfo.TrackB.Track){
        field = 'titleb[' + tagInfo.TagGeneratorRow + ']';
        value = tagInfo.TrackB.Track.Name;
        setFieldByName(tab, field, value);
        field = 'artistb[' + tagInfo.TagGeneratorRow + ']';
        value = tagInfo.TrackB.Track.Artist;
        setFieldByName(tab, field, value);
    }
}

function CreatePageOfLabels(pageIndex, tracks)
{
    var labelsPerPage = 20;
    var startIndex = pageIndex * labelsPerPage;
    if (startIndex >= 100) { return false; } // Jukebox can only hold 200 labels
    var tab = CreateSafariJukeboxTab();

    for(var i = 0; i < 20; i++)
    {
        var tagInfo = new Object();
        tagInfo.TagGeneratorRow = i + 1; // Row as in the website jukebox tag generator
        tagInfo.TrackA = new Object();
        tagInfo.TrackA.Index = startIndex + i;  // Which track in the tracks array
        if (tagInfo.TrackA.Index >= tracks.length) { return false; } // No more songs to process.
        tagInfo.TrackA.TagIndex = tagInfo.TrackA.Index + 100;   // Jukebox 3 digit number
        tagInfo.TrackA.Track = tracks[tagInfo.TrackA.Index];    // Track Info (name, artist, etc)

        tagInfo.TrackB = new Object();
        tagInfo.TrackB.Index = startIndex + i + 100; // Which track in the tracks array
        tagInfo.TrackB.TagIndex = tagInfo.TrackB.Index + 100; // Jukebox 3 digit number
        tagInfo.TrackB.Track = null;
        if (tagInfo.TrackB.Index < tracks.length) {
            tagInfo.TrackB.Track = tracks[tagInfo.TrackB.Index]; // Track Info (name, artist, etc)
        }
        console.log('******************************');
        console.log('Tag Generator Row: ' + tagInfo.TagGeneratorRow);
        console.log(tagInfo.TrackA.TagIndex + ') Title A: ' + tagInfo.TrackA.Track.Name + '\tArtist A: ' + tagInfo.TrackA.Track.Artist);

        if ( tagInfo.TrackB.Track )
        {
            console.log(tagInfo.TrackB.TagIndex + ') Title B: ' + tagInfo.TrackB.Track.Name + '\tArtist B: ' + tagInfo.TrackB.Track.Artist);
        }
        SetField(tab, tagInfo);
    }
    return true;
}

function setFieldByName(tab, fieldName, value)
{
    var js = "document.getElementsByName('" + fieldName + "')[0].value='" + value.replace(/\'/g, '\\\'') + "';";
    safari.doJavaScript(js, {in: tab});
}