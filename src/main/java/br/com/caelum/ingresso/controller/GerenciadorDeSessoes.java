package br.com.caelum.ingresso.controller;

import java.time.LocalTime;
import java.util.List;

import br.com.caelum.ingresso.model.Sessao;

public class GerenciadorDeSessoes {
	
	public boolean cabe(sessaoAtual){
	Optional<boolean> opt = sessoesExistentes.stream().map(sessaoExistente -> verificaHorarioDasSessoes(sessaoAtual,sessaoExistente)).reduce(Boolean::logicalAnd);
	return opt.orElse(true);
	}
	public boolean verficaHorarioDasSessoes(Sessao sessaoAtual, Sessao sessaoExistente){
		LocalTime horarioAtual = sessaoAtual.getHorario();
		LocalTime horarioExistente = sessaoExistente.getHorario();
		boolean ehAntes = horarioAtual.isBefore(horarioExistente);
		if(ehAntes){
			return sessaoAtual.getHorarioTermino().before(horarioExistente);
		}
	}
	public GerenciadorDeSessoes(List<Sessao>sessoes){
		this.sessoesExistentes = sessoes;
	}
}
