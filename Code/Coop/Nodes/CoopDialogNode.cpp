#include "StdAfx.h"
#include <Nodes/G2FlowBaseNode.h>

#include "IGameObject.h"
#include "Coop/Entities/DialogSynchronizer.h"

CDialogSynchronizer* GetDialogSynchronizer()
{
	IEntityClass* pDialogClass = gEnv->pEntitySystem->GetClassRegistry()->FindClass("DialogSynchronizer");
	if (!pDialogClass)
		return NULL;

	IEntityIt* iter = gEnv->pEntitySystem->GetEntityIterator();
	while (!iter->IsEnd())
	{
		if (IEntity* pEnt = iter->Next())
		{
			if (pEnt->GetClass() == pDialogClass)
			{
				if (IGameObject* pGameObject = gEnv->pGame->GetIGameFramework()->GetGameObject(pEnt->GetId()))
				{
					return (CDialogSynchronizer*)pGameObject->QueryExtension("DialogSynchronizer");
				}
			}
		}
	}

	if (gEnv->bServer)
	{
		SEntitySpawnParams params;
		params.sName = "DialogSynchronizer";
		params.pClass = pDialogClass;
		params.nFlags = ENTITY_FLAG_NEVER_NETWORK_STATIC;
		IEntity* pEnt = gEnv->pEntitySystem->SpawnEntity(params);
		if (pEnt)
		{
			if (IGameObject* pGameObject = gEnv->pGame->GetIGameFramework()->GetGameObject(pEnt->GetId()))
			{
				CryLogAlways("[CCoopDialogNode] Auto-spawned DialogSynchronizer entity ID %u", pEnt->GetId());
				return (CDialogSynchronizer*)pGameObject->QueryExtension("DialogSynchronizer");
			}
		}
	}

	return NULL;
}

class CFlowDialogNode : public CFlowBaseNode, public IDialogPlayerEventListener
{
public:
	CFlowDialogNode(SActivationInfo* pActInfo)
	{
		m_actInfo = *pActInfo;
		m_pDialogSynchronizer = NULL;
	}

	~CFlowDialogNode()
	{
		if (m_pDialogSynchronizer)
			m_pDialogSynchronizer->StopDialog();

		m_pDialogSynchronizer = NULL;
	}

	IFlowNodePtr Clone(SActivationInfo* pActInfo)
	{
		return new CFlowDialogNode(pActInfo);
	}

	virtual void GetMemoryStatistics(ICrySizer * s)
	{
		s->Add(*this);
	}

	virtual void OnDialogEvent(CDialogSession::EDialogSessionEvent event, int curLine, CDialogSession::EAbortReason abortReason)
	{
		switch (event)
		{
		case CDialogSession::eDSE_SessionStart:
			ActivateOutput(&m_actInfo, EOP_Started, true);
			break;
		case CDialogSession::eDSE_LineStarted:
			ActivateOutput(&m_actInfo, EOP_CurrentLine, curLine);
			break;
		case CDialogSession::eDSE_EndOfDialog:
			ActivateOutput(&m_actInfo, EOP_Finished, true);
			ActivateOutput(&m_actInfo, EOP_DoneFinishedOrAborted, true);
			break;
		case CDialogSession::eDSE_Aborted:
			ActivateOutput(&m_actInfo, EOP_DoneFinishedOrAborted, true);
			ActivateOutput(&m_actInfo, EOP_Aborted, true);
			ActivateOutput(&m_actInfo, EOP_LastLine, curLine);
			if (abortReason == CDialogSession::eAR_AIAborted)
				ActivateOutput(&m_actInfo, EOP_AIAbort, true);
			else if (abortReason == CDialogSession::eAR_PlayerOutOfRange)
				ActivateOutput(&m_actInfo, EOP_PlayerAbort, 1);
			else if (abortReason == CDialogSession::eAR_PlayerOutOfView)
				ActivateOutput(&m_actInfo, EOP_PlayerAbort, 2);
			else if (abortReason == CDialogSession::eAR_ActorDead)
				ActivateOutput(&m_actInfo, EOP_ActorDied, true);
			break;
		case CDialogSession::eDSE_UserStopped:
			ActivateOutput(&m_actInfo, EOP_DoneFinishedOrAborted, true);
			break;
		}
	}

	static const int MAX_ACTORS = 8;

	enum 
	{
		EIP_Play = 0,
		EIP_Stop,
		EIP_Dialog,
		EIP_StartLine,
		EIP_AIInterrupt,
		EIP_AwareDist,
		EIP_AwareAngle,
		EIP_AwareTimeOut,
		EIP_Flags,
		EIP_ActorFirst = EIP_Flags+1,
		EIP_ActorLast  = EIP_ActorFirst + MAX_ACTORS,
	};

	enum
	{
		EOP_Started = 0,
		EOP_DoneFinishedOrAborted,
		EOP_Finished,
		EOP_Aborted,
		EOP_PlayerAbort,
		EOP_AIAbort,
		EOP_ActorDied,
		EOP_LastLine,
		EOP_CurrentLine
	};

	void GetConfiguration( SFlowNodeConfig& config )
	{
		static const SInputPortConfig in_config[] = {
			InputPortConfig_Void      ("Play",_HELP("Trigger to play the Dialog")),
			InputPortConfig_Void      ("Stop",_HELP("Trigger to stop the Dialog")),
			InputPortConfig<string>   ("dialog_Dialog", _HELP("Dialog to play"), _HELP("Dialog")),
			InputPortConfig<int>      ("StartLine", 0, _HELP("Line to start Dialog from")),
			InputPortConfig<int>      ("AIInterrupt", 0, _HELP("AI interrupt behaviour: Always, MediumAlerted, Never"), 0, _UICONFIG("enum_int:Always=0,MediumAlerted=1,Never=2")),
			InputPortConfig<float>    ("AwareDistance", 0.f, _HELP("Max. Distance Player is considered as listening. 0.0 disables check.")),
			InputPortConfig<float>    ("AwareAngle", 0.f, _HELP("Max. View Angle Player is considered as listening. 0.0 disables check")),
			InputPortConfig<float>    ("AwareTimeout", 3.0f, _HELP("TimeOut until non-aware Player aborts dialog. [Effective pnly if AwareDistance or AwareAngle != 0]")),
			InputPortConfig<int>      ("Flags", 0, _HELP("Dialog Playback Flags"), 0, _UICONFIG("enum_int:None=0,FinishLineOnAbort=1")),
			InputPortConfig<EntityId> ("Actor1", _HELP("Actor 1 [EntityID]"), _HELP("Actor 1")),
			InputPortConfig<EntityId> ("Actor2", _HELP("Actor 2 [EntityID]"), _HELP("Actor 2")),
			InputPortConfig<EntityId> ("Actor3", _HELP("Actor 3 [EntityID]"), _HELP("Actor 3")),
			InputPortConfig<EntityId> ("Actor4", _HELP("Actor 4 [EntityID]"), _HELP("Actor 4")),
			InputPortConfig<EntityId> ("Actor5", _HELP("Actor 5 [EntityID]"), _HELP("Actor 5")),
			InputPortConfig<EntityId> ("Actor6", _HELP("Actor 6 [EntityID]"), _HELP("Actor 6")),
			InputPortConfig<EntityId> ("Actor7", _HELP("Actor 7 [EntityID]"), _HELP("Actor 7")),
			InputPortConfig<EntityId> ("Actor8", _HELP("Actor 8 [EntityID]"), _HELP("Actor 8")),
			{0}
		};
		static const SOutputPortConfig out_config[] = {
			OutputPortConfig_Void ("Started",_HELP("Triggered when the Dialog started.")),
			OutputPortConfig_Void ("DoneFOA",_HELP("Triggered when the Dialog ended [Finished OR Aborted]."),_HELP("Done")),
			OutputPortConfig_Void ("Done",_HELP("Triggered when the Dialog finished normally."), _HELP("Finished")),
			OutputPortConfig_Void ("Aborted",_HELP("Triggered when the Dialog was aborted.")),
			OutputPortConfig<int> ("PlayerAbort", _HELP("Triggered when the Dialog was aborted because Player was not aware.\n1=OutOfRange\n2=OutOfView")),
			OutputPortConfig_Void ("AIAbort", _HELP("Triggered when the Dialog was aborted because AI got alerted.")),
			OutputPortConfig_Void ("ActorDied", _HELP("Triggered when the Dialog was aborted because an Actor died.")),
			OutputPortConfig<int> ("LastLine", _HELP("Last line when dialog was aborted.")),
			OutputPortConfig<int> ("CurLine", _HELP("Current line. Triggered whenever a line starts.")),
			{0}
		};
		config.sDescription = _HELP("Play a Dialog - WIP");
		config.pInputPorts = in_config;
		config.pOutputPorts = out_config;
		config.SetCategory(EFLN_ADVANCED);
	}

	void ProcessEvent(EFlowEvent event, SActivationInfo* pActInfo)
	{
		switch (event)
		{
		case eFE_Initialize:
			break;
		case eFE_Activate:
			if (IsPortActive(pActInfo, EIP_Stop))
			{
				if (!m_pDialogSynchronizer)
				{
					CryLogAlways("[CCoopDialogNode] Dialog Synchronizer Not Found!");
					return;
				}

				bool bOk = m_pDialogSynchronizer->StopDialog();
				if (bOk)
					ActivateOutput(pActInfo, EOP_DoneFinishedOrAborted, true);
			}
			if (IsPortActive(pActInfo, EIP_Play))
			{
				if (gEnv->bMultiplayer && !gEnv->bServer)
				{
					// Server is the dialog authority in multiplayer; it synchronizes dialog playback to all clients via CDialogSynchronizer
					return;
				}

				if (!m_pDialogSynchronizer)
					m_pDialogSynchronizer = GetDialogSynchronizer();

				if (!m_pDialogSynchronizer)
				{
					CryLogAlways("[CCoopDialogNode] Dialog Synchronizer Not Found!");
					return;
				}

				bool bOk = m_pDialogSynchronizer->StopDialog();
				if (bOk)
					ActivateOutput(pActInfo, EOP_DoneFinishedOrAborted, true);

				string sDialog = GetPortString(pActInfo, EIP_Dialog);
				EntityId* pActors = new EntityId[8];
				for (int i = 0; i < MAX_ACTORS; i++)
				{
					pActors[i] = GetPortEntityId(pActInfo, i + EIP_ActorFirst);
				}
				const int nAIInterrupt = GetPortInt(pActInfo, EIP_AIInterrupt);
				const int nStartLine = GetPortInt(pActInfo, EIP_StartLine);
				const int fAwareDist = GetPortFloat(pActInfo, EIP_AwareDist);
				const int fAwareAngle = GetPortFloat(pActInfo, EIP_AwareAngle);
				const int fAwareTimeOut = GetPortFloat(pActInfo, EIP_AwareTimeOut);
				const int nFlags = GetPortInt(pActInfo, EIP_Flags);
				m_actInfo = *pActInfo;
				bOk = m_pDialogSynchronizer->PlayDialog(sDialog, pActors, nAIInterrupt, fAwareDist, fAwareAngle, fAwareTimeOut, nFlags, nStartLine, this);

				SAFE_DELETE_ARRAY(pActors);
			}
			break;
		}
	}

private:
	SActivationInfo m_actInfo;
	CDialogSynchronizer* m_pDialogSynchronizer;
};

REGISTER_FLOW_NODE( "Coop:PlayDialog", CFlowDialogNode );
class CFlowSPDialogNode : public CFlowDialogNode
{
public:
	CFlowSPDialogNode(SActivationInfo* pActInfo) : CFlowDialogNode(pActInfo) {}
	virtual IFlowNodePtr Clone(SActivationInfo* pActInfo) { return new CFlowSPDialogNode(pActInfo); }
};
REGISTER_FLOW_NODE( "Dialog:PlayDialog", CFlowSPDialogNode );



