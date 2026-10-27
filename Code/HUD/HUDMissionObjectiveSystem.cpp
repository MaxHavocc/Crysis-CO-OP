// -------------------------------------------------------------------------
// Crytek Source File.
// Copyright (C) Crytek GmbH, 2001-2008.
// -------------------------------------------------------------------------
#include "StdAfx.h"
#include "ISerialize.h"
#include "Game.h"
#include "HUD.h"
#include "HUDRadar.h"
#include "GameRules.h"

void CHUDMissionObjective::SetStatus(HUDMissionStatus status)
{
	if (status == m_eStatus)
		return;

	m_eStatus = status;

	if (!m_trackedEntity && m_eStatus == ACTIVATED)
	{
		string objName = m_id;
		size_t dotPos = objName.find("Objective_");
		if (dotPos != string::npos)
		{
			string entName = "MissionObjective" + objName.substr(dotPos + 10);
			if (IEntity* pEnt = gEnv->pEntitySystem->FindEntityByName(entName.c_str()))
			{
				m_trackedEntity = pEnt->GetId();
			}
		}
	}

	if (m_trackedEntity)
	{
		if (m_eStatus == ACTIVATED)
		{
			SAFE_HUD_FUNC(GetRadar()->UpdateMissionObjective(m_trackedEntity, true, m_mapLabel.c_str(), m_secondary));
		}
		else
		{
			SAFE_HUD_FUNC(GetRadar()->UpdateMissionObjective(m_trackedEntity, false, 0, false));
		}
	}

	SAFE_HUD_FUNC(UpdateObjective(this));

	m_lastTimeChanged = gEnv->pTimer->GetFrameStartTime().GetSeconds();

	static bool s_syncingObjective = false;
	if (!s_syncingObjective && g_pGame && g_pGame->GetGameRules() && gEnv->bMultiplayer)
	{
		s_syncingObjective = true;
		if (gEnv->bServer)
		{
			g_pGame->GetGameRules()->GetGameObject()->InvokeRMI(CGameRules::ClSetObjectiveStatus(), CGameRules::SetObjectiveStatusParams(m_id.c_str(), status), eRMI_ToAllClients | eRMI_NoLocalCalls);
		}
		// Notice: Clients must NEVER echo objective updates back to server to prevent infinite network loops & sound spam!
		s_syncingObjective = false;
	}
}

int CHUDMissionObjective::GetColorStatus() const
{
	int colorStatus = 0;
	switch (m_eStatus)
	{
	case ACTIVATED:
		colorStatus = 1; //green
		if(IsSecondary())
			colorStatus = 2; //yellow
		break;
	case CHUDMissionObjective::DEACTIVATED:
		break;
	case CHUDMissionObjective::COMPLETED:
		colorStatus = 4; //grey
		break;
	case CHUDMissionObjective::FAILED:
		colorStatus = 3; //red
		break;
	}

	return colorStatus;
}

const char* CHUDMissionObjectiveSystem::GetMissionObjectiveLongDescription(const char* id)
{
	const char* message = 0;
	CHUDMissionObjective* pObj = GetMissionObjective(id);
	if (pObj)
		message = pObj->GetMessage();
	return message;
}

const char* CHUDMissionObjectiveSystem::GetMissionObjectiveShortDescription(const char* id)
{
	const char* message = 0;
	CHUDMissionObjective* pObj = GetMissionObjective(id);
	if (pObj)
		message = pObj->GetShortDescription();
	return message;
}

void CHUDMissionObjectiveSystem::LoadLevelObjectives(bool forceReloading)
{
	if(!m_bLoadedObjectives || forceReloading)
	{
		m_currentMissionObjectives.clear();
		m_bLoadedObjectives = true;

		// Load base game objectives first so all campaign levels have valid text and names
		LoadLevelObjectives("Libs/UI/Objectives.xml");
		// Load global Coop objectives
		LoadLevelObjectives("Libs/UI/Objectives_Coop.xml");

		// Also try level-specific objectives
		if(gEnv->bEditor)
		{
			char *levelName = NULL;
			char *levelPath = NULL;
			g_pGame->GetIGameFramework()->GetEditorLevel(&levelName, &levelPath);
			if (levelPath)
			{
				string filename = levelPath;
				filename.append("/objectives.xml");
				LoadLevelObjectives(filename.c_str());
			}
		}
		else
		{
			ILevel *pLevel = g_pGame->GetIGameFramework()->GetILevelSystem()->GetCurrentLevel();
			if(pLevel && pLevel->GetLevelInfo())
			{
				string filename = pLevel->GetLevelInfo()->GetPath();
				filename.append("/objectives.xml");
				LoadLevelObjectives(filename.c_str());
			}
		}
	}
}

void CHUDMissionObjectiveSystem::LoadLevelObjectives(const char *filename)
{
	XmlNodeRef missionObjectives = GetISystem()->LoadXmlFile(filename);
	if (missionObjectives == 0)
		return;

	for(int tag = 0; tag < missionObjectives->getChildCount(); ++tag)
	{
		XmlNodeRef mission = missionObjectives->getChild(tag);
		for(int obj = 0; obj < mission->getChildCount(); ++obj)
		{
			XmlNodeRef objectiveNode = mission->getChild(obj);
			string id(mission->getTag());
			id.append(".");
			id.append(objectiveNode->getTag());

			// Check if already in list to avoid duplicate entries
			bool exists = false;
			for (size_t i = 0; i < m_currentMissionObjectives.size(); ++i)
			{
				if (!strcmp(m_currentMissionObjectives[i].GetID(), id.c_str()))
				{
					exists = true;
					break;
				}
			}
			if (exists)
				continue;

			const char* nameAttr = objectiveNode->getAttr("Name");
			const char* descAttr = objectiveNode->getAttr("Description");
			const char* mapLabel = objectiveNode->getAttr("MapLabel");
			const char* secondaryStr = objectiveNode->getAttr("Secondary");
			bool secondaryObjective = (secondaryStr && !stricmp(secondaryStr, "true"));

			const char* shortMsg = (nameAttr && nameAttr[0]) ? nameAttr : (descAttr ? descAttr : "");
			const char* msg = (descAttr && descAttr[0]) ? descAttr : (nameAttr ? nameAttr : "");

			string locShort = shortMsg ? shortMsg : "";
			string locMsg = msg ? msg : "";
			ILocalizationManager* pLocMgr = gEnv->pSystem ? gEnv->pSystem->GetLocalizationManager() : NULL;
			if (pLocMgr)
			{
				if (shortMsg && shortMsg[0] == '@')
				{
					ILocalizationManager::SLocalizedInfo info;
					if (pLocMgr->GetLocalizedInfo(shortMsg + 1, info) && info.sEnglish && info.sEnglish[0])
					{
						locShort = info.sEnglish;
					}
					else
					{
						wstring wloc;
						if (pLocMgr->LocalizeLabel(shortMsg, wloc, true) && !wloc.empty())
						{
							char buf[512] = {0};
							snprintf(buf, sizeof(buf) - 1, "%ls", wloc.c_str());
							locShort = buf;
						}
					}
				}
				if (msg && msg[0] == '@')
				{
					ILocalizationManager::SLocalizedInfo info;
					if (pLocMgr->GetLocalizedInfo(msg + 1, info) && info.sEnglish && info.sEnglish[0])
					{
						locMsg = info.sEnglish;
					}
					else
					{
						wstring wloc;
						if (pLocMgr->LocalizeLabel(msg, wloc, true) && !wloc.empty())
						{
							char buf[512] = {0};
							snprintf(buf, sizeof(buf) - 1, "%ls", wloc.c_str());
							locMsg = buf;
						}
					}
				}
			}

			if ((locShort.length() > 0) || (locMsg.length() > 0))
			{
				m_currentMissionObjectives.push_back(CHUDMissionObjective(this, id.c_str(), locShort.c_str(), locMsg.c_str(), mapLabel, secondaryObjective));
			}
		}
	}
}

void CHUDMissionObjectiveSystem::DeactivateObjectives(bool leaveOutRecentlyChanged)
{
	for(int i = 0; i < m_currentMissionObjectives.size(); ++i)
	{
		if(!leaveOutRecentlyChanged ||
			(m_currentMissionObjectives[i].m_lastTimeChanged - gEnv->pTimer->GetFrameStartTime().GetSeconds() > 0.2f))
		{
			bool isSilent = m_currentMissionObjectives[i].IsSilent();
			m_currentMissionObjectives[i].SetSilent(true);
			m_currentMissionObjectives[i].SetStatus(CHUDMissionObjective::DEACTIVATED);
			m_currentMissionObjectives[i].SetSilent(isSilent);
		}
	}
}

static bool MatchObjectiveID(const char* fullId, const char* queryId)
{
	if (!fullId || !queryId) return false;
	if (!stricmp(fullId, queryId)) return true;

	const char* dot = strchr(fullId, '.');
	const char* sub = dot ? (dot + 1) : fullId;
	if (!stricmp(sub, queryId)) return true;

	int fullNum = -1, queryNum = -1;
	char fullPrefix[64] = {0}, queryPrefix[64] = {0};
	if (sscanf_s(sub, "%[A-Za-z_]%d", fullPrefix, (unsigned)_countof(fullPrefix), &fullNum) == 2 &&
		sscanf_s(queryId, "%[A-Za-z_]%d", queryPrefix, (unsigned)_countof(queryPrefix), &queryNum) == 2)
	{
		if (!stricmp(fullPrefix, queryPrefix) && fullNum == queryNum)
			return true;
	}

	const char* qdot = strchr(queryId, '.');
	if (dot && qdot)
	{
		string fullMap(fullId, dot - fullId);
		string qMap(queryId, qdot - queryId);
		if (!stricmp(fullMap.c_str(), qMap.c_str()))
		{
			const char* qsub = qdot + 1;
			if (sscanf_s(sub, "%[A-Za-z_]%d", fullPrefix, (unsigned)_countof(fullPrefix), &fullNum) == 2 &&
				sscanf_s(qsub, "%[A-Za-z_]%d", queryPrefix, (unsigned)_countof(queryPrefix), &queryNum) == 2)
			{
				if (!stricmp(fullPrefix, queryPrefix) && fullNum == queryNum)
					return true;
			}
		}
	}

	return false;
}

CHUDMissionObjective* CHUDMissionObjectiveSystem::GetMissionObjective(const char* id)
{
	if (!id || !id[0])
		return NULL;

	// 1. Exact match
	for(std::vector<CHUDMissionObjective>::iterator it = m_currentMissionObjectives.begin(); it != m_currentMissionObjectives.end(); ++it)
	{
		if(!strcmp( (*it).GetID(), id))
			return &(*it);
	}

	// 2. Fuzzy match (suffix, map prefix, single/double digit e.g. Objective_2 vs Objective_02)
	for(std::vector<CHUDMissionObjective>::iterator it = m_currentMissionObjectives.begin(); it != m_currentMissionObjectives.end(); ++it)
	{
		if(MatchObjectiveID((*it).GetID(), id))
			return &(*it);
	}

	// 3. Auto-create fallback with localization attempt so raw '@' strings are never displayed
	string fallbackDesc = id;
	ILocalizationManager* pLocMgr = gEnv->pSystem ? gEnv->pSystem->GetLocalizationManager() : NULL;
	if (pLocMgr)
	{
		string queryKey = (id[0] == '@') ? (id + 1) : id;
		ILocalizationManager::SLocalizedInfo info;
		if (pLocMgr->GetLocalizedInfo(queryKey.c_str(), info) && info.sEnglish && info.sEnglish[0])
		{
			fallbackDesc = info.sEnglish;
		}
		else
		{
			string label = (id[0] == '@') ? id : ("@" + string(id));
			wstring wloc;
			if (pLocMgr->LocalizeLabel(label.c_str(), wloc, true) && !wloc.empty())
			{
				char buf[512] = {0};
				snprintf(buf, sizeof(buf) - 1, "%ls", wloc.c_str());
				fallbackDesc = buf;
			}
		}
	}

	m_currentMissionObjectives.push_back(CHUDMissionObjective(this, id, fallbackDesc.c_str(), fallbackDesc.c_str(), 0, false));
	return &m_currentMissionObjectives.back();
}

void CHUDMissionObjectiveSystem::Serialize(TSerialize ser)	//not tested!!
{
	if (ser.IsReading())
		LoadLevelObjectives(true);

	float now = gEnv->pTimer->GetFrameStartTime().GetSeconds();

	for(std::vector<CHUDMissionObjective>::iterator it = m_currentMissionObjectives.begin(); it != m_currentMissionObjectives.end(); ++it)
	{
		ser.BeginGroup("HUD_Objective");
		ser.EnumValue("ObjectiveStatus", (*it).m_eStatus, CHUDMissionObjective::FIRST, CHUDMissionObjective::LAST);
		ser.Value("trackedEntity", (*it).m_trackedEntity);
		ser.EndGroup();

		if(ser.IsReading() && (*it).m_eStatus != CHUDMissionObjective::DEACTIVATED)
		{				
			CHUDMissionObjective obj = *it;
			obj.m_lastTimeChanged = now;
			bool isSilent = obj.IsSilent();
			obj.SetSilent(true);
			SAFE_HUD_FUNC(UpdateObjective(&obj));
			obj.SetSilent(isSilent);
		}
	}
}

void CHUDMissionObjectiveSystem::GetMemoryStatistics(ICrySizer * s)
{
	s->Add(*this);
	s->AddContainer(m_currentMissionObjectives);
	for (size_t i=0; i<m_currentMissionObjectives.size(); i++)
		m_currentMissionObjectives[i].GetMemoryStatistics(s);
}

void CHUDMissionObjective::SetTrackedEntity(EntityId entityID)
{	
	if(m_trackedEntity)
		SAFE_HUD_FUNC(GetRadar()->UpdateMissionObjective(m_trackedEntity, false, 0, false));

	m_trackedEntity = entityID;

	if (m_trackedEntity && (m_eStatus == ACTIVATED))
	{
		SAFE_HUD_FUNC(GetRadar()->UpdateMissionObjective(m_trackedEntity, true, m_mapLabel.c_str(), m_secondary));
		SAFE_HUD_FUNC(UpdateObjective(this));
	}
}
