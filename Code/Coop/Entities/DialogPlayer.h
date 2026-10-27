#ifndef _DialogPlayer_H_
#define _DialogPlayer_H_

#include <IGameObject.h>
#include "../CoopSystem.h"
#include "../DialogSystem/DialogSystem.h"
#include "../DialogSystem/DialogSession.h"

class IDialogPlayerEventListener
{
public:
	virtual ~IDialogPlayerEventListener() {}
	virtual void OnDialogEvent(CDialogSession::EDialogSessionEvent event, int curLine, CDialogSession::EAbortReason abortReason) = 0;
};

class CDialogPlayer : public IDialogSessionListener
{
public:
	CDialogPlayer()
	{
		m_sessionID = 0;
		m_bIsPlaying = false;
		m_pEventListener = NULL;
	}

	~CDialogPlayer()
	{
		StopDialog();
	}

	static const int MAX_ACTORS = 8;

private:
	CDialogSystem::SessionID m_sessionID;
	bool m_bIsPlaying;
	IDialogPlayerEventListener* m_pEventListener;

protected:
	CDialogSession* GetSession()
	{
		CDialogSystem* pDS = CCoopSystem::GetInstance()->GetDialogSystem();
		if (pDS)
			return pDS->GetSession(m_sessionID);
		return 0;
	}

public:
	bool StopDialog()
	{
		m_bIsPlaying = false;
		CDialogSession* pSession = GetSession();
		if (pSession)
		{
			pSession->RemoveListener(this);

			CDialogSystem* pDS = CCoopSystem::GetInstance()->GetDialogSystem();
			if (pDS)
				pDS->DeleteSession(m_sessionID);

			m_sessionID = 0;
			return true;
		}
		return false;
	}

	bool PlayDialog(string sDialog, EntityId* pActors, int nAIInterrupt, float fAwareDist, float fAwareAngle, float fAwareTimeOut, int nFlags, int nFromLine, IDialogPlayerEventListener* pListener = NULL)
	{
		m_pEventListener = pListener;
		CDialogSystem* pDS = CCoopSystem::GetInstance()->GetDialogSystem();
		if (!pDS)
			return true;
		const string& scriptID = sDialog;
		m_sessionID = pDS->CreateSession(scriptID);
		if (m_sessionID == 0)
		{
			CryLogAlways("[CDialogPlayer] PlayDialog: Cannot create DialogSession with Script '%s'.", scriptID.c_str());
			return false;
		}

		CDialogSession* pSession = GetSession();
		assert(pSession != 0);
		if (pSession == 0)
			return false;

		// set actor flags
		CDialogSession::TActorFlags actorFlags = CDialogSession::eDACF_Default;
		switch (nFlags)
		{
		case 1:
			actorFlags = CDialogSession::eDACF_NoAbortSound;
			break;
		default:
			break;
		}

		// stage actors
		for (int i = 0; i < MAX_ACTORS; ++i)
		{
			EntityId id = pActors[i];
			if (id != 0)
			{
				pSession->SetActor(static_cast<CDialogScript::TActorID> (i), id);
				pSession->SetActorFlags(static_cast<CDialogScript::TActorID> (i), actorFlags);
			}
		}

		const int aiBehaviourInt = nAIInterrupt;
		CDialogSession::EDialogAIInterruptBehaviour aiBehaviour = CDialogSession::eDIB_InterruptAlways;
		switch (aiBehaviourInt)
		{
		case 0: aiBehaviour = CDialogSession::eDIB_InterruptAlways; break;
		case 1: aiBehaviour = CDialogSession::eDIB_InterruptMedium; break;
		case 2: aiBehaviour = CDialogSession::eDIB_InterruptNever; break;
		}
		pSession->SetAIBehaviourMode(aiBehaviour);
		pSession->SetPlayerAwarenessDistance(fAwareDist);
		pSession->SetPlayerAwarenessAngle(fAwareAngle);
		pSession->SetPlayerAwarenessGraceTime(fAwareTimeOut);

		// Validate the session
		if (pSession->Validate() == false)
		{
			CDialogScript::SActorSet currentSet = pSession->GetCurrentActorSet();
			CDialogScript::SActorSet reqSet = pSession->GetScript()->GetRequiredActorSet();
			CryLogAlways("[CDialogPlayer] PlayDialog: Session with Script '%s' cannot be validated: ", scriptID.c_str());
			for (int i = 0; i<CDialogScript::MAX_ACTORS; ++i)
			{
				if (reqSet.HasActor(i) && !currentSet.HasActor(i))
				{
					CryLogAlways("[CDialogPlayer]  Actor %d is missing.", i + 1);
				}
			}

			pDS->DeleteSession(m_sessionID);
			m_sessionID = 0;
			return false;
		}

		pSession->AddListener(this);

		const bool bPlaying = pSession->Play(nFromLine);
		if (!bPlaying)
		{
			pSession->RemoveListener(this);
			pDS->DeleteSession(m_sessionID);
			m_sessionID = 0;
		}

		return m_sessionID != 0;
	}

protected:
	// IDialogSessionListener
	virtual void SessionEvent(CDialogSession* pSession, CDialogSession::EDialogSessionEvent event)
	{
		if (pSession && pSession->GetSessionID() == m_sessionID)
		{
			const int curLine = pSession->GetCurrentLine();
			const CDialogSession::EAbortReason reason = pSession->GetAbortReason();

			if (event == CDialogSession::eDSE_SessionStart)
			{
				m_bIsPlaying = true;
			}
			else if (event == CDialogSession::eDSE_Aborted || event == CDialogSession::eDSE_EndOfDialog || event == CDialogSession::eDSE_UserStopped)
			{
				m_bIsPlaying = false;
				pSession->RemoveListener(this);
				CDialogSystem* pDS = CCoopSystem::GetInstance()->GetDialogSystem();
				if (pDS)
					pDS->DeleteSession(m_sessionID);
				m_sessionID = 0;
			}
			else if (event == CDialogSession::eDSE_SessionDeleted)
			{
				m_sessionID = 0;
				m_bIsPlaying = false;
			}

			if (m_pEventListener)
			{
				m_pEventListener->OnDialogEvent(event, curLine, reason);
			}
		}
	}
	// ~IDialogSessionListener
};

#endif
