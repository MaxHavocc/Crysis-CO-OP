#include "StdAfx.h"
#include "CoopPlayer.h"
#include "Coop/CoopCutsceneSystem.h"
#include <IConsole.h>
#include <IGameFramework.h>

CCoopPlayer::CCoopPlayer() : m_pSystemUpdateRate(0),
	m_fDetectionTimer(0),
	m_fDetectionValue(0),
	m_fLastDetectionValue(0),
	m_fNetDetectionDelay(0.f),
	m_fMusicIntensity(0.f),
	m_bMusicForceMood(false),
	m_fMusicDelay(0.f)
{
}

CCoopPlayer::~CCoopPlayer()
{
	m_pSystemUpdateRate = 0;
}

//CPlayer
bool CCoopPlayer::Init(IGameObject * pGameObject)
{
	if (!CPlayer::Init(pGameObject))
		return false;

	m_pSystemUpdateRate = gEnv->pConsole->GetCVar("ai_UpdateInterval");

	return true;
}

void CCoopPlayer::PostInit(IGameObject * pGameObject)
{
	CPlayer::PostInit(pGameObject);
}

void CCoopPlayer::Update(SEntityUpdateContext& ctx, int updateSlot)
{
	CPlayer::Update(ctx, updateSlot);
	UpdateMusic(ctx.fFrameTime);

	if (gEnv->bServer)
	{
		if (m_fNetDetectionDelay > 0.1f)
		{
			m_fNetDetectionDelay = 0.f;
			GetGameObject()->InvokeRMI(CCoopPlayer::ClUpdateAwareness(), SAwarenessParams(m_fDetectionValue),  eRMI_ToClientChannel, GetChannelId());
		}
		else
			m_fNetDetectionDelay += ctx.fFrameTime;
	}


    if (IsPlayer() && gEnv->bServer && GetEntity())
    {
        if (GetHealth() <= 0 && GetEntity()->GetAI())
        {
            gEnv->bMultiplayer = false;
 
            if (IScriptTable* pScriptTable = GetEntity()->GetScriptTable())
            {
                gEnv->pScriptSystem->BeginCall(pScriptTable, "CoopRemoveAI");
                gEnv->pScriptSystem->PushFuncParam(pScriptTable);
                gEnv->pScriptSystem->EndCall(pScriptTable);
            }

			CryLogAlways("AI Registered for Player %s", GetEntity()->GetName());
 
            gEnv->bMultiplayer = true;
        }
        else if (!GetEntity()->GetAI() && GetSpectatorMode() == eASM_None && GetHealth() > 0)
        {
            gEnv->bMultiplayer = false;
 
            if (IScriptTable* pScriptTable = GetEntity()->GetScriptTable())
            {
                gEnv->pScriptSystem->BeginCall(pScriptTable, "CoopForceAI");
                gEnv->pScriptSystem->PushFuncParam(pScriptTable);
                gEnv->pScriptSystem->EndCall(pScriptTable);
            }

			CryLogAlways("AI Unregistered for Player %s", GetEntity()->GetName());
 
            gEnv->bMultiplayer = true;
        }
    }

	// Fixes cloaking in MP for non-host players
    CNanoSuit* pNanoSuit = GetNanoSuit();
    if (pNanoSuit && gEnv->bServer)
    {
        IAIObject* pAI = GetEntity()->GetAI();
        if (pAI && pAI->CastToIAIActor() && GetEntityId() != g_pGame->GetIGameFramework()->GetClientActorId())
        {
            AgentParameters& agentParams = (AgentParameters&)pAI->CastToIAIActor()->GetParameters();
            if (pNanoSuit->GetMode() == NANOMODE_CLOAK )
            {
                agentParams.m_fCloakScale = 1.f;
                agentParams.m_fCloakScaleTarget = 1.f;
            }
            else
            {
                agentParams.m_fCloakScale = 0.f;
                agentParams.m_fCloakScaleTarget = 0.f;
            }
        }
    }

}

void CCoopPlayer::UpdateMusic(float frameTime)
{
	m_fMusicDelay += frameTime;

	if (IsClient() && m_fMusicDelay > 3.0f)
	{
		m_fMusicDelay = 0.f;

		if (!gEnv->pMusicSystem || CCoopCutsceneSystem::GetInstance()->IsPlayingCutscene())
			return;

		const char* theme = gEnv->pMusicSystem->GetTheme();
		if (!theme || !theme[0] || strcmp(theme, "island_meeting_barnes") == 0)
			return;

		const char* mood = gEnv->pMusicSystem->GetMood();
		if (!mood)
			return;

		if (!m_bMusicForceMood)
			m_fMusicIntensity = m_fDetectionValue;

		if (m_fMusicIntensity < 0.1f)
		{
			if (strcmp(mood, "incidental") != 0)
				gEnv->pMusicSystem->SetMood("incidental", false);
		}
		else if (m_fMusicIntensity < 0.2f)
		{
			if (strcmp(mood, "ambient") != 0)
				gEnv->pMusicSystem->SetMood("ambient", false);
		}
		else if (m_fMusicIntensity < 0.65f)
		{
			if (strcmp(mood, "middle") != 0)
				gEnv->pMusicSystem->SetMood("middle", false);
		}
		else
		{
			if (strcmp(mood, "action") != 0)
				gEnv->pMusicSystem->SetMood("action", false);
		}
	}
}

void CCoopPlayer::PostUpdate(float frameTime)
{
	CPlayer::PostUpdate(frameTime);

	if (gEnv->bServer)
	{
		// Called here not to interfere with AI system.
		UpdateDetectionValue(frameTime);
	}
	
}

bool CCoopPlayer::NetSerialize(TSerialize ser, EEntityAspects aspect, uint8 profile, int flags)
{
	if (!CPlayer::NetSerialize(ser, aspect, profile, flags))
		return false;

	return true;
}
//~CPlayer

void CCoopPlayer::UpdateDetectionValue(float frameTime)
{
	m_fDetectionTimer += frameTime;
	float updateRate = (m_pSystemUpdateRate ? m_pSystemUpdateRate->GetFVal() : 0.1f);
	if (m_fDetectionTimer >= updateRate + 0.05f)
	{
		m_fDetectionTimer = 0.0f;
		IAIObject* pAI = GetEntity() ? GetEntity()->GetAI() : NULL;
		if (pAI && gEnv->pAISystem)
		{
			SAIDetectionLevels aiDetectionLevels;
			gEnv->pAISystem->GetDetectionLevels(pAI, aiDetectionLevels);
			m_fDetectionValue = max(max(aiDetectionLevels.puppetExposure, aiDetectionLevels.puppetThreat),
									max(aiDetectionLevels.vehicleExposure, aiDetectionLevels.vehicleThreat));
		}
		else if (gEnv->pAISystem && GetEntityId() == g_pGame->GetIGameFramework()->GetClientActorId())
		{
			SAIDetectionLevels aiDetectionLevels;
			gEnv->pAISystem->GetDetectionLevels(0, aiDetectionLevels);
			m_fDetectionValue = max(max(aiDetectionLevels.puppetExposure, aiDetectionLevels.puppetThreat),
									max(aiDetectionLevels.vehicleExposure, aiDetectionLevels.vehicleThreat));
		}
	}
}

IMPLEMENT_RMI(CCoopPlayer, ClUpdateAwareness)
{
	m_fDetectionValue = params.awarenessFloat;
    return true;    // Always return true - false will drop connection
}