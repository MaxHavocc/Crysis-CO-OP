Script.ReloadScript("Scripts/Entities/Sound/MusicThemeSelector.lua");

-- Overridden for Crysis Co-op synchronization
local Old_MusicThemeSelector = MusicThemeSelector;

if (MusicThemeSelector) then
	local orig_Event_SetTheme = MusicThemeSelector.Event_SetTheme;
	function MusicThemeSelector:Event_SetTheme()
		if (orig_Event_SetTheme) then
			orig_Event_SetTheme(self);
		else
			Sound.SetMusicTheme(self.Properties.sTheme, self.Properties.bForceChange, self.Properties.bKeepMood, self.Properties.nDelayInSec);
			if (self.Properties.sDefaultMood ~= "") then
				Sound.SetDefaultMusicMood(self.Properties.sDefaultMood);
			end
			local bNotKeepMood = self.Properties.bKeepMood == 0;
			if (self.Properties.sMood ~= "" and bNotKeepMood) then
				Sound.SetMusicMood(self.Properties.sMood, 1);
			end
		end

		-- Broadcast to all Co-op clients so background/event music plays everywhere
		if (g_gameRules and g_gameRules.allClients and g_gameRules.allClients.ClSetMusicTheme) then
			g_gameRules.allClients:ClSetMusicTheme(self.Properties.sTheme, self.Properties.sMood);
		end
	end
end
