#include <StdAfx.h>

#include "CoopCutsceneSystem.h"

#include <IGameFramework.h>

#include <IEntitySystem.h>

#include <IActorSystem.h>

#include <IScriptSystem.h>

#include <I3DEngine.h>

#include "Game.h"

#include "HUD/HUD.h"

#include "HUD/HUDFader.h"



CCoopCutsceneSystem CCoopCutsceneSystem::s_instance = CCoopCutsceneSystem();



CCoopCutsceneSystem::CCoopCutsceneSystem() : m_bPlayingCutscene(false),

    m_bPlayingCutsceneLastFrame(false),

    m_bCutsceneBlending(false),

    m_bAwaitingAshoreBoot(false),

    m_cameraEntityId(0),

    m_fCameraFOV(DEG2RAD(60.0f))

{

}



CCoopCutsceneSystem::~CCoopCutsceneSystem()

{

}



void CCoopCutsceneSystem::Register()

{

    if (!gEnv->bEditor)

        gEnv->pGame->GetIGameFramework()->GetIViewSystem()->AddListener(this);

}



void CCoopCutsceneSystem::Unregister()

{

    if (!gEnv->bEditor)

        gEnv->pGame->GetIGameFramework()->GetIViewSystem()->RemoveListener(this);

}



void CCoopCutsceneSystem::Update(float fFrameTime)

{

    // Native CryEngine flowgraphs (FG_cine_0, FG_cine_1) handle all sub-triggers,

    // sounds, dialogs, and sequence chains natively without hardcoded timers.



    // Active cutscene camera tracking

    if (m_bPlayingCutscene && m_cameraEntityId != 0 && !gEnv->bEditor)

    {

        IEntity* pCameraEntity = gEnv->pEntitySystem->GetEntity(m_cameraEntityId);

        if (pCameraEntity)

        {

            IView* pView = gEnv->pGame->GetIGameFramework()->GetIViewSystem()->GetActiveView();

            if (pView)

            {

                SViewParams* currParams = (SViewParams*)pView->GetCurrentParams();

                if (currParams)

                {

                    currParams->position = pCameraEntity->GetWorldPos();

                    currParams->rotation = pCameraEntity->GetWorldRotation();

                    currParams->fov = (m_fCameraFOV > 0.01f) ? m_fCameraFOV : DEG2RAD(60.0f);



                    if (!m_bPlayingCutsceneLastFrame)

                    {

                        m_bCutsceneBlending = currParams->blend;

                        currParams->blend = false;

                    }

                    else

                    {

                        currParams->blend = m_bCutsceneBlending;

                    }

                }

            }

        }

    }



    m_bPlayingCutsceneLastFrame = m_bPlayingCutscene;

}



bool CCoopCutsceneSystem::OnBeginCutScene(IAnimSequence* pSeq, bool bResetFX)

{

    m_bPlayingCutscene = true;



    if (pSeq && gEnv->pEntitySystem)

    {

        const char* seqName = pSeq->GetName();

        if (seqName)

        {

            if (strcmp(seqName, "cine_0_intro") == 0)

            {

                // Ensure night/dawn Time of Day is set

                if (gEnv->p3DEngine && gEnv->p3DEngine->GetTimeOfDay())

                {

                    gEnv->p3DEngine->GetTimeOfDay()->SetTime(5.5f, true);

                }



                if (IEntity* pCam = gEnv->pEntitySystem->FindEntityByName("cine_0_intro_cam"))

                {

                    m_cameraEntityId = pCam->GetId();

                    m_fCameraFOV = DEG2RAD(50.0f);

                }

            }

            else if (strcmp(seqName, "cine_1_c17intro") == 0)

            {

                if (IEntity* pCam = gEnv->pEntitySystem->FindEntityByName("cine_1_shakeCamera"))

                {

                    m_cameraEntityId = pCam->GetId();

                    m_fCameraFOV = DEG2RAD(60.0f);

                }

            }

            else if (strcmp(seqName, "cine_1_parachute_seqence") == 0)

            {

                // In base Crysis, freefall parachute sequence is FIRST PERSON!

                // Player retains mouse-look and sees their own arms. Do NOT override camera!

                m_cameraEntityId = 0;



                if (IActor* pClientActor = gEnv->pGame->GetIGameFramework()->GetClientActor())

                {

                    if (IEntity* pActorEnt = pClientActor->GetEntity())

                    {

                        pActorEnt->Hide(false);

                    }

                }

            }

            else if (strcmp(seqName, "cine_1_player_hitByScout") == 0)

            {

                if (IEntity* pCam = gEnv->pEntitySystem->FindEntityByName("cine_1_player_ScoutHit_shakeCam"))

                {

                    m_cameraEntityId = pCam->GetId();

                    m_fCameraFOV = DEG2RAD(35.0f);

                }

            }

        }

    }



    if (gEnv->bServer && pSeq)

    {

        const char* seqName = pSeq->GetName();

        if (seqName && seqName[0])

        {

            // For in-game cutscenes (like Aztec), safely teleport co-op partner to ground cutscene spot

            bool isIntro = (strstr(seqName, "cine_1") || strstr(seqName, "intro") || strstr(seqName, "cine_0") || strstr(seqName, "C17_Tray"));

            if (!isIntro)

            {

                if (IActor* pHostActor = gEnv->pGame->GetIGameFramework()->GetClientActor())

                {

                    Vec3 hostPos = pHostActor->GetEntity()->GetWorldPos();

                    IActorIteratorPtr pIt = gEnv->pGame->GetIGameFramework()->GetIActorSystem()->CreateActorIterator();

                    while (IActor* pOther = pIt->Next())

                    {

                        if (pOther != pHostActor && pOther->IsPlayer())

                        {

                            Vec3 partnerPos = hostPos;

                            pOther->GetEntity()->SetPos(partnerPos);

                        }

                    }

                }

            }



            // Broadcast cutscene sequence to all clients so co-op partner plays synchronously

            char cmd[256];

            sprintf_s(cmd, "if g_gameRules and g_gameRules.allClients and g_gameRules.allClients.ClPlayCutscene then g_gameRules.allClients:ClPlayCutscene('%s') end", seqName);

            gEnv->pScriptSystem->ExecuteBuffer(cmd, strlen(cmd));

        }

    }



    return true;

}



bool CCoopCutsceneSystem::OnEndCutScene(IAnimSequence* pSeq)

{

    if (pSeq)

    {

        const char* seqName = pSeq->GetName();

        if (seqName)

        {

            if (strcmp(seqName, "cine_0_intro") == 0 ||

                strcmp(seqName, "cine_1_c17intro") == 0 ||

                strcmp(seqName, "cine_1_c17_extro") == 0 ||

                strcmp(seqName, "cine_1_parachute_seqence") == 0)

            {

                // Seamless transition to next intro sequence in CHUD::OnEndCutScene - keep cutscene view active!

                return true;

            }



            if (gEnv->bServer)

            {

                char endCmd[256];

                sprintf_s(endCmd, "if g_gameRules and g_gameRules.OnCutsceneEnded then g_gameRules:OnCutsceneEnded('%s') end", seqName ? seqName : "");

                gEnv->pScriptSystem->ExecuteBuffer(endCmd, strlen(endCmd));

            }

        }

    }

    if (IActor* pLocalActor = gEnv->pGame->GetIGameFramework()->GetClientActor())

    {

        if (IEntity* pEnt = pLocalActor->GetEntity())

        {

            pEnt->Hide(false);

            pEnt->Invisible(false);

        }

        if (CPlayer* pLocalPl = static_cast<CPlayer*>(pLocalActor))

        {

            

            pLocalPl->Draw(true);

        }

    }

    m_bPlayingCutscene = false;

    m_cameraEntityId = 0;

    return true;

}



void CCoopCutsceneSystem::OnPlayCutSceneSound(IAnimSequence* pSeq, ISound* pSound)

{

}



bool CCoopCutsceneSystem::OnCameraChange(const SCameraParams& cameraParams)

{

    if (cameraParams.cameraEntityId != 0)

        m_cameraEntityId = cameraParams.cameraEntityId;

    if (cameraParams.fFOV > 0.01f)

        m_fCameraFOV = cameraParams.fFOV;



    return true;

}

